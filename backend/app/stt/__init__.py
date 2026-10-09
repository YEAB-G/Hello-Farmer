from app.config import settings
from app.stt.base import BaseSTTProvider
from app.stt.gemini_stt import GeminiSTTProvider
from app.stt.groq_stt import GroqSTTProvider
from app.stt.whisper_local import WhisperLocalSTTProvider


def get_stt_provider(provider_type: str | None = None) -> BaseSTTProvider:
    ptype = (provider_type or getattr(settings, "STT_PROVIDER", "gemini")).lower()
    if ptype == "groq" and not settings.GEMINI_API_KEY and settings.GROQ_API_KEY:
        return GroqSTTProvider()
    elif settings.GEMINI_API_KEY:
        return GeminiSTTProvider()
    elif settings.GROQ_API_KEY:
        return GroqSTTProvider()
    return WhisperLocalSTTProvider()
