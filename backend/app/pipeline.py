"""Core independent voice & text pipeline for Hello Farmer.

Signature: process_utterance(audio, session, text_override) -> Response(audio, text, metadata)
Decoupled from Asterisk, testable from raw audio/WAV files,
and directly reusable behind any text or voice API.
"""
import asyncio
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings
from app.database.session import async_session_factory
from app.farmer_context.extraction import (
    extract_context_from_utterance,
)
from app.language.detect import detect_text_language
from app.llm.base import LLMAnswer
from app.llm.chain import LLMFallbackChain
from app.rag.faq_cache import match_agricultural_faq
from app.rag.retrieve import retrieve_passages
from app.rag.store import persist_web_passages_to_rag
from app.rag.web_search import search_agricultural_web
from app.safety.guardrails import validate_and_guard
from app.stt import get_stt_provider
from app.tts import get_tts_provider
from app.weather.location import format_spoken_location_confirmation, resolve_location
from app.weather.provider import get_weather_provider
from app.weather.risk import WeatherRiskAnalyzer

logger = logging.getLogger("hello_farmer.pipeline")


def reformulate_search_query(user_text: str, session: "SessionState") -> str:
    """Reformulate conversational follow-ups into complete standalone agricultural queries."""
    text_clean = user_text.strip()
    words = text_clean.split()

    is_followup = (
        len(words) <= 5
        or any(w in text_clean for w in [
            "መድሃኒቱ", "መጠኑ", "እንዴት", "በስንት", "ከዛ", "በኋላ", "መቼ",
            "it", "dosage", "cure", "treat", "interval", "spray", "apply"
        ])
    )

    context_tokens = []
    if session.extracted_crop and session.extracted_crop not in text_clean:
        context_tokens.append(session.extracted_crop)
    if session.extracted_symptoms and session.extracted_symptoms not in text_clean:
        context_tokens.append(session.extracted_symptoms)

    if is_followup and context_tokens:
        enriched_query = f"{' '.join(context_tokens)} {text_clean}"
        logger.info(f"🔍 [QUERY REFORMULATION] '{text_clean}' -> '{enriched_query}'")
        return enriched_query
    return text_clean

WEATHER_INTENT_KEYWORDS = {
    "am": [
        "ዝናብ", "የአየር ሁኔታ", "መርጨት", "ንፋስ", "ፀሐይ", "ውርጭ", "በረዶ", "ደመና",
        "የዛሬ አየር", "የዛሬው አየር", "የዛሬ ሙቀት", "የዛሬው ሙቀት", "ሙቀት", "ሙቀቱ",
        "የአየር ጠባይ", "ቀዝቃዛ", "ሞቃት", "ትኩሳት", "ስንት ዲግሪ", "ዲግሪ", "የሙቀት መጠን"
    ],
    "om": [
        "roob", "bokkaa", "haala qilleensaa", "biif", "bubbee", "aduu", "cabiitii", "duumessa",
        "ho'a", "hoo'a", "qorra", "tempereechara", "digirii", "qabbana"
    ],
    "en": [
        "weather", "rain", "spray", "spraying", "wind", "temperature", "forecast",
        "temp", "degrees", "celsius", "hot", "cold", "humidity", "rainy", "sunny", "cloudy"
    ],
    "ti": [
        "ዝናብ", "ኩነታት ኣየር", "ንፋስ", "ፀሓይ", "ቁሪ", "በረድ", "ደመና", "ሙቐት", "ኩነታት አየር", "ዲግሪ"
    ],
    "so": [
        "roob", "cimilada", "dabayl", "qorrax", "kuleyl", "heerkulka"
    ],
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
    has_consented: bool = True
    turn_count: int = 0
    consecutive_silence_count: int = 0
    call_stage: str = "GREETING"
    location_name: str | None = None
    location_region: str | None = None
    location_zone: str | None = None
    location_woreda: str | None = None
    location_latitude: float | None = None
    location_longitude: float | None = None
    location_confidence: float | None = None
    agroecological_zone: str | None = None
    extracted_crop: str | None = None
    extracted_symptoms: str | None = None
    extracted_location: str | None = None
    last_question: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)


class ResponseMetadata(BaseModel):
    grounded: bool
    needs_referral: bool = False
    evidence_mode: str = "rag_grounded"  # rag_grounded | location_aware_model_answer | clarification_needed | expert_referral
    sources_used: list[dict[str, Any]] = Field(default_factory=list)
    location_used: str | None = None
    confidence: float = 1.0
    topic: str | None = None
    follow_up_question: str | None = None
    safety_note: str | None = None
    stt_provider: str | None = None
    llm_provider: str | None = None
    tts_provider: str | None = None
    fallback_used: bool = False
    latency_ms: dict[str, float] = Field(default_factory=dict)
    answer_en_gloss: str | None = None
    user_transcript: str | None = None
    language: str = "am"


class Response(BaseModel):
    audio: bytes | None = None  # 8 kHz 16-bit mono PCM bytes for telephony
    text: str
    metadata: ResponseMetadata


def is_weather_intent(text: str, language: str = "am") -> bool:
    """Check if query is asking for weather, temperature, or spraying conditions."""
    lower = text.lower()
    kw_list = WEATHER_INTENT_KEYWORDS.get(language, []) + WEATHER_INTENT_KEYWORDS["en"]
    return any(k in lower for k in kw_list)


def is_spraying_query(text: str, language: str = "am") -> bool:
    """Check if query is specifically asking about pesticide/fungicide spraying."""
    lower = text.lower()
    kw_list = SPRAYING_KEYWORDS.get(language, []) + SPRAYING_KEYWORDS["en"]
    return any(k in lower for k in kw_list)


GOODBYE_KEYWORDS = {
    "am": [
        "ይበቃል", "ለዛሬ ይበቃል", "ደህና ሁን", "ደህና ሁኚ", "ደህና ሁኑ", "ቻው", "በቃኝ", "በቃ",
        "ጨርሻለሁ", "አመሰግናለሁ", "እናመሰግናለን", "አመሰግናለሁ ይበቃል", "እናመሰግናለን ይበቃል",
        "የለም", "የለም በቃኝ", "የለም አመሰግናለሁ", "ምንም የለም", "የለም አመሰግናለው",
        "በቃ እናመሰግናለን", "ደህና ዋሉ", "ደህና እደሩ", "ምንም ጥያቄ የለኝም", "ጥያቄ የለኝም",
        "ሌላ ጥያቄ የለኝም", "ምንም ሌላ ጥያቄ የለኝም", "ጥያቄ የለም", "ምንም የለኝም", "የለኝም",
        "ቸሻለሁ", "ሻሻለው", "ቸቻሎ", "ጨርሻለው", "ጨረስኩ", "ጨርሰናል", "ተጠናቋል"
    ],
    "om": [
        "nagaatti", "ga'aadha", "ammaaf ga'aadha", "galatoomi", "xumureera", "nagaan bulaa",
        "lakki", "lakki galatoomaa", "gaaffii hin qabu", "gaaffii biraa hin qabu", "gaaffiin hin jiru"
    ],
    "en": [
        "goodbye", "bye", "that's all", "that is all", "thank you that's enough", "done",
        "no thank you", "no thanks", "nothing else", "i don't have a question", "i dont have a question",
        "no question", "no questions", "i have no question", "i have no questions", "no more questions",
        "nothing more", "i'm done", "im done", "that's it", "thats all",
        "i have finished", "i finished", "finished", "im finished", "i'm finished", "have finished", "finish", "finished now"
    ],
    "ti": [
        "ደሓን ኩኑ", "ደሓን ዋዓሉ", "የቐንየለይ", "ይኣክል", "ሕቶ የብለይን", "ካልእ ሕቶ የብለይን", "የለን"
    ],
    "so": [
        "nabad gelyo", "waa intaas", "mahadsanid", "su'aal kale ma qabo", "wax kale ma jiraan"
    ],
}

GREETING_KEYWORDS = {
    "am": ["ሰላም", "እንዴት ነህ", "እንዴት ነሽ", "እንደምን አለህ", "ሰላም ነህ"],
    "om": ["akkam", "akkam jirtu", "akkami", "nagaadha"],
    "en": ["hello", "hi", "how are you"],
}


def is_goodbye_intent(text: str, language: str = "am") -> bool:
    lower = text.lower().strip()
    if any(k in lower for k in ("finish", "finished", "done", "that's all", "thats all", "no more")):
        return True
    kw_list = GOODBYE_KEYWORDS.get(language, []) + GOODBYE_KEYWORDS["en"]
    if any(k in lower for k in kw_list):
        return True
    no_q_patterns = [
        "not have any question", "don't have any question", "dont have any question",
        "have no question", "have no questions", "no question", "no questions",
        "no more questions", "i am done", "im done", "that is all",
        "ጥያቄ የለኝም", "ጥያቄ የለም", "ምንም የለኝም", "የለኝም አመሰግናለሁ", "በቃኝ", "ይበቃል",
        "gaaffii hin qabu", "gaaffii biraa hin qabu", "ሕቶ የብለይን"
    ]
    return any(p in lower for p in no_q_patterns)


def is_greeting_intent(text: str, language: str = "am") -> bool:
    import re
    cleaned = re.sub(r"[^\w\s]", "", text).lower().strip()
    if len(cleaned.split()) <= 3:
        kw_list = GREETING_KEYWORDS.get(language, []) + GREETING_KEYWORDS["en"]
        return any(k in cleaned for k in kw_list)
    return False


def is_off_topic_query(text: str, language: str = "am") -> bool:
    """Detect queries unrelated to agriculture, crops, or livestock."""
    OFF_TOPIC_WORDS = [
        "konkolaataa", "makiinaa", "makina", "መኪና", "ቴሌ", "tele", "football", "kubbaa", "ኳስ",
        "visa", "ፓስፖርት", "passport", "film", "movie", "ሙዚቃ", "muuziqaa", "music",
        "መንግስት መኪና", "gurgura konkolaataa"
    ]
    t = text.lower()
    return any(w in t for w in OFF_TOPIC_WORDS)



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
    stt_provider_name = "text_input"
    stt_fallback_used = False

    # 1. Speech-to-Text / Text Resolution
    if text_override:
        user_text = text_override.strip()
    elif audio_bytes:
        stt_t0 = time.time()
        stt = get_stt_provider()
        transcript_obj = await stt.transcribe(audio_bytes, language=session.language)
        user_text = transcript_obj.text.strip()
        stt_provider_name = getattr(transcript_obj, "provider", stt.__class__.__name__)
        stt_fallback_used = getattr(transcript_obj, "fallback_used", False)
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
        if session.language == "am":
            goodbye_reply = "ስለደወሉ እናመሰግናለን! መልካም የእርሻ ጊዜ ይሁንልዎ። ደህና ይሁኑ።"
            gloss = "Thank you for calling! Wishing you a great farming season. Goodbye."
        elif session.language == "om":
            goodbye_reply = "Waan bilbiltaniif guddaa galatoomaa! Yeroo qonnaa gaarii isiniif haa ta'u. Nagaatti!"
            gloss = "Thank you for calling! Wishing you a great farming season. Goodbye."
        elif session.language == "ti":
            goodbye_reply = "ስለ ዝደወልኩም የቐንየልና! ጽቡቕ ናይ ሕርሻ እዋን ይኹነልኩም። ደሓን ኩኑ።"
            gloss = "Thank you for calling! Wishing you a great farming season. Goodbye."
        else:
            goodbye_reply = "Thank you for calling Hello Farmer! Wishing you a fruitful farming season. Goodbye!"
            gloss = "Thank you for calling Hello Farmer! Wishing you a fruitful farming season. Goodbye!"

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
                answer_en_gloss=gloss,
                user_transcript=user_text,
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
                user_transcript=user_text,
            ),
        )

    # 2d. Off-topic Non-Agricultural Query Flow
    if is_off_topic_query(user_text, session.language):
        referral_reply = (
            "ይቅርታ፣ ይህ ጥያቄ ከግብርና ውጭ ነው። ለግብርና መረጃ እባክዎ የአካባቢዎን የግብርና ልማት ጣቢያ ባለሙያ ያማክሩ ወይም በስምንት ዜሮ ሁለት ስምንት (8028) ይደውሉ።"
            if session.language == "am"
            else "Dhiifama, gaaffiin kun qonnaan ala. Odeeffannoo qonnaaf maaloo ogeessa qonnaa naannoo keessanii gaafadhaa yookiin bilbila 8028 irratti bilbilaa."
        )
        audio_out = b""
        if synthesize_audio:
            tts = get_tts_provider()
            audio_out = await tts.synthesize(referral_reply, language=session.language)
        return Response(
            audio=audio_out,
            text=referral_reply,
            metadata=ResponseMetadata(
                grounded=False,
                topic="off_topic",
                needs_referral=True,
                confidence=0.9,
                latency_ms={"total": round((time.time() - t0) * 1000, 1)},
                answer_en_gloss="This query is not agricultural. Please consult local extension worker or call 8028.",
                user_transcript=user_text,
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


    # 3. Weather / Spraying / Temperature Intent Flow
    if is_weather_intent(user_text, session.language):
        weather_t0 = time.time()
        loc_match = resolve_location(user_text)
        is_default_location = False
        if not loc_match and session.location_name:
            loc_match = resolve_location(session.location_name)
        if not loc_match and session.extracted_location:
            loc_match = resolve_location(session.extracted_location)
        if not loc_match and session.location_woreda:
            loc_match = resolve_location(session.location_woreda)
        if not loc_match and session.location_region:
            loc_match = resolve_location(session.location_region)

        if not loc_match:
            ask_loc_msg = (
                "የአየር ሁኔታ መረጃ ለማግኘት እባክዎ አካባቢዎን ወይም ወረዳዎን ይንገሩኝ?"
                if session.language == "am"
                else "Haala qilleensaa baruuf maaloo naannoo yookiin aanaa keessan natti himaa?"
            )
            audio_out = b""
            if synthesize_audio:
                tts = get_tts_provider()
                audio_out = await tts.synthesize(ask_loc_msg, language=session.language)
            return Response(
                audio=audio_out,
                text=ask_loc_msg,
                metadata=ResponseMetadata(
                    grounded=True,
                    topic="weather_location_request",
                    confidence=0.95,
                    latency_ms={"total": round((time.time() - t0) * 1000, 1)},
                    answer_en_gloss="Please specify your woreda or nearby area to get weather forecast.",
                    user_transcript=user_text,
                ),
            )

        # Update confirmed location in session
        if not is_default_location and loc_match:
            session.extracted_location = loc_match.name

        weather_provider = get_weather_provider()
        forecast = await weather_provider.get_forecast(
            latitude=loc_match.latitude if loc_match else 8.54,
            longitude=loc_match.longitude if loc_match else 39.27,
            location_name=loc_match.name if loc_match else "Adama",
            days=3,
        )

        t_max = round(getattr(forecast, "temperature_max_c", 25.0) or getattr(forecast, "max_temperature_c", 25.0))
        t_min = round(getattr(forecast, "temperature_min_c", 14.0) or getattr(forecast, "min_temperature_c", 14.0))
        precip = getattr(forecast, "precipitation_sum_mm", 0.0) or 0.0

        if is_default_location:
            if session.language == "om":
                conf_phrase = "Naannoo qonnaa gidduugaleessaa (Adaamaa)tti,"
            elif session.language == "en":
                conf_phrase = "In the central farming zone (Adama),"
            elif session.language == "ti":
                conf_phrase = "ኣብ ማእከላይ ዞባ ሕርሻ (ኣዳማ)፣"
            else:
                conf_phrase = "በማዕከላዊ የእርሻ አካባቢ (አዳማ)፣"
        else:
            conf_phrase = format_spoken_location_confirmation(loc_match, session.language)

        if is_spraying_query(user_text, session.language):
            # Spraying analysis
            spray_eval = WeatherRiskAnalyzer.evaluate_spraying(forecast)
            if session.language == "om":
                raw_reply = f"{conf_phrase} {spray_eval.reason_om}"
            elif session.language == "en":
                status_txt = "Conditions are suitable for spraying." if spray_eval.can_spray else "Spraying is not recommended due to weather risks."
                raw_reply = f"{conf_phrase} {status_txt} {spray_eval.reason_en}"
            elif session.language == "ti":
                raw_reply = f"{conf_phrase} {'ናይ ምዝራእ ወይ መድሃኒት ምንጻግ ኩነታት ጽቡቕ እዩ' if spray_eval.can_spray else 'ብሰንኪ ኩነታት ኣየር ምንጻግ ኣይምከርን'}።"
            else:
                raw_reply = f"{conf_phrase} {spray_eval.reason_am}"
            topic = "weather_spraying"
        else:
            # Full weather and temperature report
            if session.language == "om":
                sky_om = "roobni cimaan waan eegamuuf of eeggannoo godhaa" if forecast.is_heavy_rain else ("roobni ni eegama" if precip > 2.0 else "haalli qilleensaa qulqulluu fi bokkaa kan hin qabneedha")
                raw_reply = f"{conf_phrase} Ho'i har'aa guddaan digirii {t_max} yoo ta'u, xiqqaan digirii {t_min} dha. {sky_om}."
            elif session.language == "en":
                sky_en = "heavy rain is expected so take precautions" if forecast.is_heavy_rain else ("light rain is likely" if precip > 2.0 else "mostly fair and dry conditions are expected")
                raw_reply = f"{conf_phrase} Today's high temperature is {t_max} degrees Celsius and low is {t_min} degrees. {sky_en}."
            elif session.language == "ti":
                sky_ti = "ከቢድ ዝናብ ስለ ዝጽበ ጥንቃቐ ግበሩ" if forecast.is_heavy_rain else ("ዝናብ ክህሉ ይኽእል እዩ" if precip > 2.0 else "ዝተረጋገአን ደረቕን ኩነታት ኣየር ይጽበ")
                raw_reply = f"{conf_phrase} ናይ ሎሚ ዝለዓለ ሙቐት {t_max} ዲግሪ ሴንቲግሬድ ክኸውን እንከሎ፣ ዝተሓተ ድማ {t_min} ዲግሪ ሴንቲግሬድ እዩ። {sky_ti}።"
            else:
                sky_am = "ከፍተኛ ዝናብ ስለሚጠበቅ አስፈላጊውን ጥንቃቄ ያድርጉ" if forecast.is_heavy_rain else ("አነስተኛ ዝናብ ሊኖር ይችላል" if precip > 2.0 else "የተረጋጋና ዝናብ የሌለበት አየር ይጠበቃል")
                raw_reply = f"{conf_phrase} የዛሬው ከፍተኛ ሙቀት {t_max} ዲግሪ ሴንቲግሬድ ሲሆን ዝቅተኛው {t_min} ዲግሪ ሴንቲግሬድ ነው። {sky_am}።"
            topic = "weather_forecast"

        # Transliterate digits to words
        try:
            from app.safety.guardrails import replace_digits_with_words
        except ImportError:
            from backend.app.safety.guardrails import replace_digits_with_words
        reply_text = replace_digits_with_words(raw_reply, language=session.language)

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
                user_transcript=user_text,
            ),
        )

    # 3b. Check Semantic FAQ Cache for Instant Verified Solutions (<50ms)
    faq_match = match_agricultural_faq(user_text, language=session.language)
    if faq_match:
        latencies["total"] = round((time.time() - t0) * 1000, 1)
        audio_out = b""
        if synthesize_audio:
            tts = get_tts_provider()
            audio_out = await tts.synthesize(faq_match.answer, language=session.language)

        session.history.append({"role": "caller", "text": user_text})
        session.history.append({"role": "assistant", "text": faq_match.answer})

        return Response(
            audio=audio_out,
            text=faq_match.answer,
            metadata=ResponseMetadata(
                grounded=True,
                topic=faq_match.topic,
                needs_referral=False,
                confidence=faq_match.confidence,
                sources_used=[
                    {"title": f"[VERIFIED FAQ] {faq_match.source_title}", "tier": 1, "score": 1.0}
                ],
                latency_ms=latencies,
                answer_en_gloss=faq_match.english_gloss,
                user_transcript=user_text,
            ),
        )

    # 4. Agricultural Agronomy RAG Flow
    rag_t0 = time.time()

    # Reformulate query for contextual multi-turn follow-ups
    search_query = reformulate_search_query(user_text, session)

    # Resolve structured location match if available
    loc_match = None
    target_loc_name = session.location_name or session.extracted_location
    if target_loc_name:
        loc_match = resolve_location(target_loc_name, region_hint=session.location_region)
        if loc_match:
            session.location_name = loc_match.name
            session.location_region = loc_match.region
            session.location_zone = loc_match.zone
            session.location_woreda = loc_match.woreda
            session.location_latitude = loc_match.latitude
            session.location_longitude = loc_match.longitude
            session.location_confidence = loc_match.confidence
            session.agroecological_zone = loc_match.agroecological_zone

    # Priority 1: Fast local vector DB retrieval from pgvector with location awareness
    retrieved_passages_list = []
    try:
        async with async_session_factory() as db_session:
            retrieved_passages_list = await retrieve_passages(
                query=search_query,
                session=db_session,
                top_k=4,
                crop_filter=session.extracted_crop,
                location=loc_match,
                region_filter=session.location_region,
            )
    except Exception as e:
        logger.warning("Local DB retrieval error: %s", e)

    # Priority 2: Only fallback to live web search if local database returned few/no results
    web_passages = []
    if len(retrieved_passages_list) < 2:
        try:
            web_passages = await asyncio.wait_for(
                search_agricultural_web(
                    user_text=search_query,
                    crop=session.extracted_crop,
                    language=session.language,
                    max_passages=3,
                ),
                timeout=3.5,
            )
            if web_passages:
                asyncio.create_task(
                    persist_web_passages_to_rag(
                        passages=web_passages,
                        crop=session.extracted_crop,
                        language=session.language,
                    )
                )
        except Exception as e:
            logger.debug("Live web search fallback: %s", e)

    latencies["rag"] = round((time.time() - rag_t0) * 1000, 1)

    # Combine: LIVE WEB PASSAGES COME FIRST, followed by local DB passages
    retrieved_dicts = []
    for wp in web_passages:
        retrieved_dicts.append({
            "chunk_id": wp["chunk_id"],
            "title": f"[LIVE WEB ADVISORY] {wp['title']}",
            "source_tier": "tier_1",
            "text": wp["text"],
        })
    for p in retrieved_passages_list:
        geo_tag = f" [{p.geographic_tier.upper()}]" if p.geographic_tier != "national" else ""
        retrieved_dicts.append({
            "chunk_id": p.chunk_id,
            "title": f"[LOCAL EXTENSION GUIDE{geo_tag}] {p.document_title}",
            "source_tier": f"tier_{p.source_tier}",
            "text": p.content,
        })

    # Retain retrieved_dicts without injecting fake passages if RAG returned nothing
    # Build sources list for metadata with geographic tier attribution
    sources_used = []
    for wp in web_passages:
        sources_used.append({
            "title": f"Live Web: {wp['title']}",
            "tier": 1,
            "score": wp.get("score", 0.98),
            "stored_in_rag": True,
            "geographic_tier": "national",
        })
    for p in retrieved_passages_list:
        sources_used.append({
            "title": p.document_title,
            "tier": p.source_tier,
            "score": p.score,
            "geographic_tier": p.geographic_tier,
            "locality_match": p.locality_match,
        })

    # Local Weather check for spraying or field actions if location known
    weather_summary = None
    if loc_match or (session.location_latitude and session.location_longitude):
        try:
            wp = get_weather_provider()
            lat = loc_match.latitude if loc_match else session.location_latitude
            lon = loc_match.longitude if loc_match else session.location_longitude
            fc = await wp.get_forecast(latitude=lat, longitude=lon, days=1)
            spray_eval = WeatherRiskAnalyzer.evaluate_spraying(fc)
            weather_summary = {
                "location": loc_match.name if loc_match else session.location_name,
                "region": loc_match.region if loc_match else session.location_region,
                "spraying_advisory": spray_eval.reason_om if session.language == "om" else spray_eval.reason_am,
                "can_spray": spray_eval.can_spray,
                "temp_c": fc.temperature_max_c,
                "rain_prob": fc.precipitation_probability_max,
            }
        except Exception as e:
            logger.debug("Weather context fetch error: %s", e)

    # 5. LLM Answer Generation with full location & agroecological context
    llm_t0 = time.time()
    chain = LLMFallbackChain()
    farmer_ctx = {
        "crop": session.extracted_crop or "",
        "symptoms": session.extracted_symptoms or "",
        "growth_stage": getattr(extracted, "growth_stage", "") or "",
        "location": session.location_name or session.extracted_location or "",
        "region": session.location_region or (loc_match.region if loc_match else ""),
        "zone": session.location_zone or (loc_match.zone if loc_match else ""),
        "woreda": session.location_woreda or (loc_match.woreda if loc_match else ""),
        "agroecological_zone": session.agroecological_zone or (loc_match.agroecological_zone if loc_match else "Midland"),
    }

    raw_answer: LLMAnswer = await chain.generate_response(
        transcript=user_text,
        retrieved_passages=retrieved_dicts,
        conversation_history=session.history,
        farmer_context=farmer_ctx,
        weather_info=weather_summary,
        language=session.language,
    )
    latencies["llm"] = round((time.time() - llm_t0) * 1000, 1)

    # 6. Safety Guardrails & Validation
    safe_answer = validate_and_guard(
        answer=raw_answer,
        retrieved_passages=retrieved_dicts,
        language=session.language,
    )

    # 6. TTS Audio Synthesis
    audio_out = b""
    tts_provider_name = None
    if synthesize_audio:
        tts_t0 = time.time()
        tts = get_tts_provider()
        tts_provider_name = getattr(tts, "provider_name", tts.__class__.__name__)
        audio_out = await tts.synthesize(safe_answer.answer, language=session.language)
        latencies["tts"] = round((time.time() - tts_t0) * 1000, 1)

    latencies["total"] = round((time.time() - t0) * 1000, 1)

    # Record turn in session history
    session.history.append({"role": "caller", "text": user_text})
    session.history.append({"role": "assistant", "text": safe_answer.answer})

    return Response(
        audio=audio_out,
        text=safe_answer.answer,
        metadata=ResponseMetadata(
            grounded=safe_answer.is_grounded,
            needs_referral=safe_answer.needs_referral,
            evidence_mode=getattr(safe_answer, "evidence_mode", ("rag_grounded" if retrieved_dicts else "location_aware_model_answer")),
            sources_used=sources_used,
            location_used=getattr(safe_answer, "location_used", None) or session.location_name,
            confidence=safe_answer.confidence,
            topic=session.extracted_crop or "agronomy",
            follow_up_question=getattr(safe_answer, "follow_up_question", None),
            safety_note=getattr(safe_answer, "safety_note", None),
            stt_provider=stt_provider_name,
            llm_provider=getattr(raw_answer, "provider", getattr(settings, "LLM_PROVIDER", "groq")),
            tts_provider=tts_provider_name,
            fallback_used=stt_fallback_used or getattr(raw_answer, "provider", "") != getattr(settings, "LLM_PROVIDER", "groq"),
            latency_ms=latencies,
            answer_en_gloss=safe_answer.english_gloss,
            user_transcript=user_text,
            language=session.language,
        ),
    )
