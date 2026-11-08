"""TTS provider factory."""
try:
    from app.config import settings
    from app.tts.base import BaseTTSProvider
    from app.tts.edge_tts_provider import EdgeTTSProvider
    from app.tts.fallback_synth import FallbackSynthProvider
    from app.tts.gemini_tts_provider import GeminiTTSProvider
    from app.tts.piper_local import PiperLocalTTSProvider
except ImportError:
    from backend.app.config import settings
    from backend.app.tts.base import BaseTTSProvider
    from backend.app.tts.edge_tts_provider import EdgeTTSProvider
    from backend.app.tts.fallback_synth import FallbackSynthProvider
    from backend.app.tts.gemini_tts_provider import GeminiTTSProvider
    from backend.app.tts.piper_local import PiperLocalTTSProvider


def get_tts_provider(provider_type: str | None = None) -> BaseTTSProvider:
    """Return configured TTS provider with automatic fallback hierarchy."""
    ptype = (provider_type or getattr(settings, "TTS_PROVIDER", "edge_tts")).lower()
    if ptype in ("piper", "piper_local", "local"):
        return PiperLocalTTSProvider()
    elif ptype == "fallback":
        return FallbackSynthProvider()
    elif ptype in ("edge_tts", "edge", "google"):
        try:
            return EdgeTTSProvider()
        except Exception:
            return PiperLocalTTSProvider()
    elif ptype == "gemini":
        try:
            return GeminiTTSProvider()
        except Exception:
            return EdgeTTSProvider()

    # Default to Edge-TTS provider with local fallback
    return EdgeTTSProvider()
