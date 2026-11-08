"""Smart Multilingual Speech-to-Text (STT) Router.

Dynamically routes speech recognition based on language requirements:
1. Amharic ('am'):
   -> Hugging Face Local snapwre/hohe-asr-amharic (fine-tuned CTC model, 0% hallucination, fast CPU inference).
2. English ('en'):
   -> Groq Whisper (whisper-large-v3, top-tier English accuracy, ~250ms latency).
3. Ethiopian Regional Languages ('om' Afaan Oromo, 'ti' Tigrinya, 'so' Somali):
   -> Google Gemini API (gemini-3.5-flash-lite, native multi-lingual African language support, free tier).
"""
import asyncio
import logging
import re
import time
from typing import Optional

try:
    from app.config import settings
    from app.language.detect import detect_text_language
    from app.stt.base import BaseSTTProvider, Transcript
    from app.stt.gemini_stt import GeminiSTTProvider
    from app.stt.groq_stt import GroqSTTProvider
    from app.stt.hf_stt import HuggingFaceSTTProvider
except ImportError:
    from backend.app.config import settings
    from backend.app.language.detect import detect_text_language
    from backend.app.stt.base import BaseSTTProvider, Transcript
    from backend.app.stt.gemini_stt import GeminiSTTProvider
    from backend.app.stt.groq_stt import GroqSTTProvider
    from backend.app.stt.hf_stt import HuggingFaceSTTProvider

logger = logging.getLogger("hello_farmer.stt.router")


class MultilingualSTTRouter(BaseSTTProvider):
    """Routes audio transcription to the optimal engine based on language."""

    def __init__(self):
        self.hohe_provider = HuggingFaceSTTProvider()
        self.groq_provider = GroqSTTProvider()
        self.gemini_provider = GeminiSTTProvider(model_name=getattr(settings, "GEMINI_STT_MODEL", "gemini-3.5-flash-lite"))

    async def transcribe(
        self,
        wav_path_or_bytes: str | bytes,
        language: str = "am",
        **kwargs,
    ) -> Transcript:
        t0 = time.perf_counter()
        raw_lang = (language or "am").lower().strip()

        # ====================================================
        # Route 1: English ('en') -> Groq Whisper
        # ====================================================
        if raw_lang in ("en", "english"):
            logger.info("Routing STT to Groq Whisper for English...")
            res = await self.groq_provider.transcribe(wav_path_or_bytes, language="en", **kwargs)
            res.language = "en"
            res.detected_language = "en"
            return res

        # ====================================================
        # Route 2: Ethiopian Regional Languages -> Gemini API
        # (Afaan Oromo 'om', Tigrinya 'ti', Somali 'so')
        # ====================================================
        if raw_lang in ("om", "oromo", "afaan_oromo", "ti", "tigrinya", "tigrigna", "so", "somali", "soomaali"):
            norm_code = "om" if "om" in raw_lang or "oromo" in raw_lang else ("ti" if "ti" in raw_lang else "so")
            logger.info("Routing STT to Gemini API for Ethiopian language '%s'...", norm_code)
            res = await self.gemini_provider.transcribe(wav_path_or_bytes, language=norm_code, **kwargs)
            res.language = norm_code
            res.detected_language = norm_code
            return res

        # ====================================================
        # Route 3: Amharic ('am') -> Local Fine-Tuned Hohe ASR
        # With automatic cross-lingual detection fallback
        # ====================================================
        logger.info("Routing STT to local Hohe ASR for Amharic...")
        hohe_res = await self.hohe_provider.transcribe(wav_path_or_bytes, language="am", **kwargs)

        text = (hohe_res.text or "").strip()

        # If Hohe transcribed clean Amharic (Ethiopic Ge'ez characters present and non-empty), return
        geez_chars = len(re.findall(r"[\u1200-\u137F]", text))
        if text and geez_chars >= 2:
            # Check if this might be Tigrinya orthography
            det_lang, det_conf = detect_text_language(text, stored_preference="am")
            if det_lang == "ti" and det_conf >= 0.85:
                # Tigrinya detected; verify with Gemini Tigrinya for optimal fidelity
                try:
                    ti_res = await self.gemini_provider.transcribe(wav_path_or_bytes, language="ti", **kwargs)
                    if ti_res.text and len(ti_res.text.strip()) > 2:
                        ti_res.language = "ti"
                        ti_res.detected_language = "ti"
                        return ti_res
                except Exception:
                    pass
            hohe_res.language = "am"
            hohe_res.detected_language = "am"
            return hohe_res

        # If Hohe produced empty text or transliterated non-Amharic, check via Gemini STT first
        logger.info("Checking Amharic via Gemini STT...")
        try:
            gem_res = await self.gemini_provider.transcribe(wav_path_or_bytes, language="am", **kwargs)
            g_text = (gem_res.text or "").strip()
            if g_text and len(g_text) >= 1:
                gem_res.language = "am"
                gem_res.detected_language = "am"
                return gem_res
        except Exception as e:
            logger.debug("Gemini Amharic check error: %s", e)

        # Check for English via Groq Whisper only if caller actually spoke English
        logger.info("Checking for English via Groq Whisper...")
        try:
            whisper_res = await self.groq_provider.transcribe(wav_path_or_bytes, language="en", **kwargs)
            w_text = (whisper_res.text or "").strip()
            if w_text and len(w_text.split()) >= 1 and whisper_res.confidence >= 0.60:
                det_lang, conf = detect_text_language(w_text, stored_preference=None)
                if det_lang == "en" or re.search(r"[a-zA-Z]{3,}", w_text):
                    logger.info("Detected English utterance via Groq Whisper: '%s'", w_text)
                    whisper_res.language = "en"
                    whisper_res.detected_language = "en"
                    return whisper_res
        except Exception as e:
            logger.debug("Whisper English check error: %s", e)

        # Check for other Ethiopian languages (Oromo/Somali/Tigrinya) via Gemini
        logger.info("Checking for Ethiopian regional languages via Gemini API...")
        try:
            gemini_res = await self.gemini_provider.transcribe(wav_path_or_bytes, language="auto", **kwargs)
            g_text = (gemini_res.text or "").strip()
            if g_text and len(g_text) >= 2:
                det_lang, conf = detect_text_language(g_text, stored_preference=None)
                gemini_res.language = det_lang
                gemini_res.detected_language = det_lang
                logger.info("Detected '%s' utterance via Gemini: '%s'", det_lang, g_text)
                return gemini_res
        except Exception as e:
            logger.debug("Gemini regional language check error: %s", e)

        # Fallback to whatever Hohe or Whisper returned
        return hohe_res
