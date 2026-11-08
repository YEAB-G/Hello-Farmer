try:
    from app.config import settings
    from app.stt.base import BaseSTTProvider
    from app.stt.cascade_stt import CascadingSTTProvider
    from app.stt.gemini_stt import GeminiSTTProvider
    from app.stt.groq_stt import GroqSTTProvider
    from app.stt.hf_stt import HuggingFaceSTTProvider
    from app.stt.router_stt import MultilingualSTTRouter
    from app.stt.whisper_local import WhisperLocalSTTProvider
except ImportError:
    from backend.app.config import settings
    from backend.app.stt.base import BaseSTTProvider
    from backend.app.stt.cascade_stt import CascadingSTTProvider
    from backend.app.stt.gemini_stt import GeminiSTTProvider
    from backend.app.stt.groq_stt import GroqSTTProvider
    from backend.app.stt.hf_stt import HuggingFaceSTTProvider
    from backend.app.stt.router_stt import MultilingualSTTRouter
    from backend.app.stt.whisper_local import WhisperLocalSTTProvider

_STT_CACHE: dict[str, BaseSTTProvider] = {}


def get_stt_provider(provider_type: str | None = None) -> BaseSTTProvider:
    ptype = (provider_type or getattr(settings, "STT_PROVIDER", "multilingual")).lower()
    if ptype not in _STT_CACHE:
        if ptype in ("router", "multilingual", "multi", "hf", "huggingface", "hohe"):
            _STT_CACHE[ptype] = MultilingualSTTRouter()
        elif ptype == "groq":
            _STT_CACHE[ptype] = GroqSTTProvider()
        elif ptype == "gemini":
            _STT_CACHE[ptype] = GeminiSTTProvider()
        elif ptype == "whisper_local":
            _STT_CACHE[ptype] = WhisperLocalSTTProvider()
        else:
            _STT_CACHE[ptype] = MultilingualSTTRouter()
    return _STT_CACHE[ptype]
