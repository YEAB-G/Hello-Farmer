"""TTS provider factory."""
from app.config import settings
from app.tts.base import BaseTTSProvider
from app.tts.edge_tts_provider import EdgeTTSProvider
from app.tts.fallback_synth import FallbackSynthProvider


def get_tts_provider(provider_type: str | None = None) -> BaseTTSProvider:
    ptype = provider_type or getattr(settings, "TTS_PROVIDER", "edge_tts")
    if ptype == "fallback":
        return FallbackSynthProvider()
    try:
        return EdgeTTSProvider()
    except Exception:
        return FallbackSynthProvider()
