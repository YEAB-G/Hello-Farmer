"""Abstract interface and caching layer for Text-to-Speech (TTS) providers.

All implementations synthesize text to 8 kHz 16-bit signed linear mono PCM
(Asterisk AudioSocket format) with SHA-256 caching.
"""
import hashlib
import re
from abc import ABC, abstractmethod
from pathlib import Path


class BaseTTSProvider(ABC):
    def __init__(self, cache_dir: str = "backend/cache/tts"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, text: str, voice: str, language: str) -> Path:
        """Calculate SHA-256 cache file path for (language, voice, text)."""
        key = f"{language}:{voice}:{text}".encode()
        digest = hashlib.sha256(key).hexdigest()
        return self.cache_dir / f"{digest}.pcm"

    def split_into_sentences(self, text: str) -> list[str]:
        """Split text into spoken sentence chunks on punctuation."""
        # Handle Ethiopic sentence stops (።, ፧) as well as Latin (. ! ?)
        chunks = re.split(r"(?:[።፧\.\!\?]+|\n+)", text)
        return [c.strip() for c in chunks if c.strip()]

    @abstractmethod
    async def _synthesize_raw(self, text: str, voice: str | None = None, language: str = "am") -> bytes:
        """Synthesize raw audio bytes from provider (to be downsampled if needed)."""

    async def synthesize(self, text: str, voice: str | None = None, language: str = "am") -> bytes:
        """Synthesize text into cached 8 kHz 16-bit mono linear PCM audio.

        Args:
            text: Text to synthesize.
            voice: Voice name or model identifier.
            language: Target ISO language code ('am' or 'om').

        Returns:
            8 kHz 16-bit signed linear mono PCM bytes ready for telephony streaming.
        """
        if not text or not text.strip():
            return b""

        actual_voice = voice or ("am-ET-AmehaNeural" if language == "am" else "default")
        cache_path = self.get_cache_path(text.strip(), actual_voice, language)

        # Return cached audio if present
        if cache_path.exists():
            return cache_path.read_bytes()

        # Generate audio via provider implementation
        raw_pcm_8k = await self._synthesize_raw(text.strip(), actual_voice, language)

        # Write to cache
        if raw_pcm_8k:
            try:
                cache_path.write_bytes(raw_pcm_8k)
            except Exception:
                pass

        return raw_pcm_8k
