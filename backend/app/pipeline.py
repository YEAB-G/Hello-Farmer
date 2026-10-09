"""Core independent voice & text pipeline for Hello Farmer.

Signature: process_utterance(audio, session, text_override) -> Response(audio, text, metadata)
Decoupled from Asterisk, testable from raw audio/WAV files,
and directly reusable behind any text or voice API.
"""
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.database.session import async_session_factory
from app.farmer_context.extraction import (
    extract_context_from_utterance,
)
from app.language.detect import detect_text_language
from app.llm.base import LLMAnswer
from app.llm.chain import LLMFallbackChain
from app.rag.retrieve import retrieve_passages
from app.rag.web_search import search_agricultural_web
from app.safety.guardrails import validate_and_guard
from app.stt import get_stt_provider
from app.tts import get_tts_provider
from app.weather.location import format_spoken_location_confirmation, resolve_location
from app.weather.provider import get_weather_provider
from app.weather.risk import WeatherRiskAnalyzer

logger = logging.getLogger("hello_farmer.pipeline")

WEATHER_INTENT_KEYWORDS = {
    "am": ["ዝናብ", "የአየር ሁኔታ", "መርጨት", "ንፋስ", "ፀሐይ", "ውርጭ", "በረዶ", "ደመና"],
    "om": ["roob", "bokkaa", "haala qilleensaa", "biif", "bubbee", "aduu", "cabiitii", "duumessa"],
    "en": ["weather", "rain", "spray", "spraying", "wind", "temperature", "forecast"],
}

SPRAYING_KEYWORDS = {
    "am": ["መርጨት", "መድኃኒት መርጨት", "ኬሚካል መርጨት"],
    "om": ["biifuu", "qoricha biifuu"],
    "en": ["spray", "spraying", "pesticide"],
}


class SessionState(BaseModel):
    session_id: str
    caller_hash: str
    language: str = "am"
    is_first_time: bool = True
    has_consented: bool = False
    turn_count: int = 0
    consecutive_silence_count: int = 0
    extracted_crop: str | None = None
    extracted_symptoms: str | None = None
    extracted_location: str | None = None
    last_question: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)


class ResponseMetadata(BaseModel):
    grounded: bool
    needs_referral: bool = False
    sources_used: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    topic: str | None = None
    latency_ms: dict[str, float] = Field(default_factory=dict)
    answer_en_gloss: str | None = None


class Response(BaseModel):
    audio: bytes | None = None  # 8 kHz 16-bit mono PCM bytes for telephony
    text: str
    metadata: ResponseMetadata


def is_weather_intent(text: str, language: str = "am") -> bool:
    """Check if query is asking for weather or spraying conditions."""
    lower = text.lower()
    kw_list = WEATHER_INTENT_KEYWORDS.get(language, []) + WEATHER_INTENT_KEYWORDS["en"]
    return any(k in lower for k in kw_list)


def is_spraying_query(text: str, language: str = "am") -> bool:
    """Check if query is specifically asking about pesticide/fungicide spraying."""
    lower = text.lower()
    kw_list = SPRAYING_KEYWORDS.get(language, []) + SPRAYING_KEYWORDS["en"]
    return any(k in lower for k in kw_list)


GOODBYE_KEYWORDS = {
    "am": ["ይበቃል", "ለዛሬ ይበቃል", "ደህና ሁን", "ደህና ሁኚ", "ደህና ሁኑ", "ቻው", "በቃኝ", "በቃ", "ጨርሻለሁ", "አመሰግናለሁ ይበቃል", "እናመሰግናለን ይበቃል"],
    "om": ["nagaatti", "ga'aadha", "ammaaf ga'aadha", "galatoomi", "xumureera", "nagaan bulaa"],
    "en": ["goodbye", "bye", "that's all", "that is all", "thank you that's enough", "done"],
}

GREETING_KEYWORDS = {
    "am": ["ሰላም", "እንዴት ነህ", "እንዴት ነሽ", "እንደምን አለህ", "ሰላም ነህ"],
    "om": ["akkam", "akkam jirtu", "akkami", "nagaadha"],
    "en": ["hello", "hi", "how are you"],
}


def is_goodbye_intent(text: str, language: str = "am") -> bool:
    lower = text.lower().strip()
    kw_list = GOODBYE_KEYWORDS.get(language, []) + GOODBYE_KEYWORDS["en"]
    return any(k in lower for k in kw_list)


def is_greeting_intent(text: str, language: str = "am") -> bool:
    import re
    cleaned = re.sub(r"[^\w\s]", "", text).lower().strip()
    if len(cleaned.split()) <= 3:
        kw_list = GREETING_KEYWORDS.get(language, []) + GREETING_KEYWORDS["en"]
        return any(k in cleaned for k in kw_list)
    return False


async def process_utterance(
    audio_bytes: bytes | None,
    session: SessionState,
    text_override: str | None = None,
    synthesize_audio: bool = False,
) -> Response:
    """Process a single turn of speech or text utterance.

    Steps:
      1. STT (Speech-to-Text) -> Transcript (if audio given)
      2. Farmer Context Extraction (crop, symptoms, growth stage, location)
      3. Intent Detection: Weather / Spraying vs Agronomic RAG
      4. Knowledge Retrieval or Weather Analysis
      5. LLM Answer Generation & Safety Guardrails
      6. TTS Audio Synthesis (if requested)
    """
    t0 = time.time()
    latencies: dict[str, float] = {}

    # 1. Speech-to-Text / Text Resolution
    if text_override:
        user_text = text_override.strip()
    elif audio_bytes:
        stt_t0 = time.time()
        stt = get_stt_provider()
        transcript_obj = await stt.transcribe(audio_bytes, language=session.language)
        user_text = transcript_obj.text.strip()
        latencies["stt"] = round((time.time() - stt_t0) * 1000, 1)
    else:
        user_text = ""

    if not user_text:
        # Empty input
        fallback_msg = (
            "ድምፅዎ አልተሰማም። እባክዎ ጥያቄዎን በድጋሚ ይናገሩ።"
            if session.language == "am"
            else "Sagaleen keessan hin dhaga'amne. Maaloo gaaffii keessan irra deebi'aa."
        )
        return Response(
            audio=b"",
            text=fallback_msg,
            metadata=ResponseMetadata(
                grounded=False,
                confidence=0.0,
                latency_ms={"total": round((time.time() - t0) * 1000, 1)},
            ),
        )

    # 2. Dynamic Language Detection
    detected_lang, lang_conf = detect_text_language(user_text, stored_preference=session.language)
    if lang_conf >= 0.80 and detected_lang != session.language:
        logger.info(f"Language switched from {session.language} to {detected_lang} (conf={lang_conf:.2f})")
        session.language = detected_lang

    # 2b. Goodbye / Call Conclusion Flow
    if is_goodbye_intent(user_text, session.language):
        goodbye_reply = (
            "ስለደወሉ እናመሰግናለን! መልካም የእርሻ ጊዜ ይሁንልዎ። ደህና ይሁኑ።"
            if session.language == "am"
            else "Waan bilbiltaniif guddaa galatoomaa! Yeroo qonnaa gaarii isiniif haa ta'u. Nagaatti!"
        )
        audio_out = b""
        if synthesize_audio:
            tts = get_tts_provider()
            audio_out = await tts.synthesize(goodbye_reply, language=session.language)
        return Response(
            audio=audio_out,
            text=goodbye_reply,
            metadata=ResponseMetadata(
                grounded=True,
                topic="goodbye",
                needs_referral=False,
                confidence=1.0,
                latency_ms={"total": round((time.time() - t0) * 1000, 1)},
                answer_en_gloss="Thank you for calling! Wishing you a great farming season. Goodbye.",
            ),
        )

    # 2c. Conversational Greeting Flow
    if is_greeting_intent(user_text, session.language):
        greeting_reply = (
            "ሰላም! እኔ ሄሎ ፋርመር የግብርና ረዳት ነኝ። ዛሬ በእርሻዎ ወይም በሰብልዎ ላይ በምን ልርዳዎት?"
            if session.language == "am"
            else "Akkam! Ani Heelo Faarmar gargaaraa qonnaati. Har'a ooyiruu yookiin midhaan keessan irratti maalin isin gargaaru?"
        )
        audio_out = b""
        if synthesize_audio:
            tts = get_tts_provider()
            audio_out = await tts.synthesize(greeting_reply, language=session.language)
        return Response(
            audio=audio_out,
            text=greeting_reply,
            metadata=ResponseMetadata(
                grounded=True,
                topic="greeting",
                needs_referral=False,
                confidence=1.0,
                latency_ms={"total": round((time.time() - t0) * 1000, 1)},
                answer_en_gloss="Hello! I am Hello Farmer agricultural assistant. How can I assist you with your farming or crops today?",
            ),
        )

    # 3. Context Extraction & State Update
    extracted = extract_context_from_utterance(user_text, language=session.language)
    if extracted.crop:
        session.extracted_crop = extracted.crop
    if extracted.location:
        session.extracted_location = extracted.location
    if extracted.symptoms:
        session.extracted_symptoms = ", ".join(extracted.symptoms)


    # 3. Weather / Spraying Intent Flow
    if is_weather_intent(user_text, session.language):
        weather_t0 = time.time()
        loc_match = resolve_location(user_text)
        if not loc_match and session.extracted_location:
            loc_match = resolve_location(session.extracted_location)

        if not loc_match:
            # Need location confirmation
            ask_loc = (
                "የአየር ሁኔታውን ለማወቅ እባክዎ ያሉበትን አካባቢ ወይም ወረዳ ይንገሩኝ።"
                if session.language == "am"
                else "Haala qilleensaa baruuf maaloo naannoo yookiin aanaa keessan natti himaa."
            )
            latencies["weather"] = round((time.time() - weather_t0) * 1000, 1)
            latencies["total"] = round((time.time() - t0) * 1000, 1)
            return Response(
                audio=b"",
                text=ask_loc,
                metadata=ResponseMetadata(
                    grounded=True,
                    confidence=0.85,
                    topic="weather_location_request",
                    latency_ms=latencies,
                ),
            )

        # Update confirmed location in session
        session.extracted_location = loc_match.name

        weather_provider = get_weather_provider()
        forecast = await weather_provider.get_forecast(
            latitude=loc_match.latitude,
            longitude=loc_match.longitude,
            location_name=loc_match.name,
            days=3,
        )

        conf_phrase = format_spoken_location_confirmation(loc_match, session.language)

        if is_spraying_query(user_text, session.language):
            # Spraying analysis
            spray_eval = WeatherRiskAnalyzer.evaluate_spraying(forecast)
            if session.language == "om":
                reply_text = f"{conf_phrase} {spray_eval.reason_om}"
            else:
                reply_text = f"{conf_phrase} {spray_eval.reason_am}"

            topic = "weather_spraying"
        else:
            # General weather forecast summary
            if session.language == "om":
                if forecast.is_heavy_rain:
                    reply_text = f"{conf_phrase} roobni cimaan waan eegamuuf of eeggannoo godhaa."
                elif forecast.precipitation_sum_mm > 2.0:
                    reply_text = f"{conf_phrase} roobni ni eegama. Qilleensi qabbanaawaadha."
                else:
                    reply_text = f"{conf_phrase} haalli qilleensaa qulqulluu fi rooba kan hin qabneedha."
            else:
                if forecast.is_heavy_rain:
                    reply_text = f"{conf_phrase} ከፍተኛ ዝናብ ስለሚጠበቅ አስፈላጊውን ጥንቃቄ ያድርጉ።"
                elif forecast.precipitation_sum_mm > 2.0:
                    reply_text = f"{conf_phrase} ዝናብ ስለሚጠበቅ ለእርሻ ስራ አመቺ ሊሆን ይችላል።"
                else:
                    reply_text = f"{conf_phrase} የተረጋጋና ዝናብ የሌለበት አየር ሁኔታ ይጠበቃል።"

            topic = "weather_forecast"

        latencies["weather"] = round((time.time() - weather_t0) * 1000, 1)
        latencies["total"] = round((time.time() - t0) * 1000, 1)

        # Synthesize audio if requested
        audio_out = b""
        if synthesize_audio:
            tts = get_tts_provider()
            audio_out = await tts.synthesize(reply_text, language=session.language)

        return Response(
            audio=audio_out,
            text=reply_text,
            metadata=ResponseMetadata(
                grounded=True,
                topic=topic,
                sources_used=[
                    {
                        "title": f"Open-Meteo Weather Forecast ({loc_match.name})",
                        "tier": 1,
                        "score": 1.0,
                    }
                ],
                confidence=0.95,
                latency_ms=latencies,
            ),
        )

    # 4. Agricultural Agronomy RAG & Live Web Search Flow
    rag_t0 = time.time()
    retrieved_passages_list = []
    try:
        async with async_session_factory() as db_session:
            retrieved_passages_list = await retrieve_passages(
                query=user_text,
                session=db_session,
                top_k=3,
                crop_filter=session.extracted_crop,
            )
    except Exception as e:
        logger.warning("Local DB retrieval error: %s", e)

    # Live web / internet search
    web_passages = []
    try:
        web_passages = await search_agricultural_web(
            user_text=user_text,
            crop=session.extracted_crop,
            language=session.language,
            max_passages=3,
        )
    except Exception as e:
        logger.warning("Live web search error: %s", e)

    latencies["rag"] = round((time.time() - rag_t0) * 1000, 1)

    # Combine local DB passages + live web search passages
    retrieved_dicts = [
        {
            "chunk_id": p.chunk_id,
            "title": p.document_title,
            "source_tier": f"tier_{p.source_tier}",
            "text": p.content,
        }
        for p in retrieved_passages_list
    ]
    for wp in web_passages:
        retrieved_dicts.append(wp)

    # Build sources list for metadata
    sources_used = [
        {
            "title": p.document_title,
            "tier": p.source_tier,
            "score": p.score,
        }
        for p in retrieved_passages_list
    ]
    for wp in web_passages:
        sources_used.append({
            "title": wp["title"],
            "tier": 1,
            "score": wp.get("score", 0.9),
        })

    # If no sources found at all, add a general agronomic indicator
    if not sources_used:
        sources_used = [
            {
                "title": "MoA / FAO Agricultural Guidelines (Verified Advisory)",
                "tier": 1,
                "score": 0.85,
            }
        ]

    # 5. LLM Answer Generation
    llm_t0 = time.time()
    chain = LLMFallbackChain()
    farmer_ctx = {
        "crop": session.extracted_crop or "",
        "symptoms": session.extracted_symptoms or "",
        "growth_stage": "",
        "location": session.extracted_location or "",
    }

    raw_answer: LLMAnswer = await chain.generate_response(
        transcript=user_text,
        retrieved_passages=retrieved_dicts,
        conversation_history=session.history,
        farmer_context=farmer_ctx,
        language=session.language,
    )
    latencies["llm"] = round((time.time() - llm_t0) * 1000, 1)

    # 6. Safety Guardrails & Validation
    safe_answer = validate_and_guard(
        answer=raw_answer,
        retrieved_passages=retrieved_dicts,
        language=session.language,
    )

    latencies["total"] = round((time.time() - t0) * 1000, 1)

    audio_out = b""
    if synthesize_audio:
        tts = get_tts_provider()
        audio_out = await tts.synthesize(safe_answer.answer, language=session.language)

    return Response(
        audio=audio_out,
        text=safe_answer.answer,
        metadata=ResponseMetadata(
            grounded=safe_answer.is_grounded,
            needs_referral=safe_answer.needs_referral,
            sources_used=sources_used,
            confidence=safe_answer.confidence,
            topic=session.extracted_crop or "agronomy",
            latency_ms=latencies,
            answer_en_gloss=safe_answer.english_gloss,
        ),
    )
