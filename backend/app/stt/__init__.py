"""STT provider factory."""
from app.config import settings
from app.stt.base import BaseSTTProvider
from app.stt.gemini_stt import GeminiSTTProvider
from app.stt.whisper_local import WhisperLocalSTTProvider


def get_stt_provider(provider_type: str | None = None) -> BaseSTTProvider:
    ptype = provider_type or getattr(settings, "STT_PROVIDER", "whisper")
    if ptype == "gemini":
        return GeminiSTTProvider()
    return WhisperLocalSTTProvider()
