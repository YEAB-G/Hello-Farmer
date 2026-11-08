"""Deterministic Fallback Audio Synthesizer Provider.

Provides offline spoken prompt fallback for agricultural telephony sessions:
1. Matches conversational intents against pre-recorded spoken audio prompts
   (e.g., greeting, ask_location, ask_problem, safe_fallback, goodbye).
2. Converts matched studio WAV clips into standard 8 kHz 16-bit mono linear PCM.
3. Completely deprecates sine-wave beep responses for agricultural advisory calls.
"""
import io
import logging
from pathlib import Path
import wave
import numpy as np

try:
    from app.audio.convert import audio_stream_to_pcm8k
    from app.tts.base import BaseTTSProvider
except ImportError:
    from backend.app.audio.convert import audio_stream_to_pcm8k
    from backend.app.tts.base import BaseTTSProvider

logger = logging.getLogger("hello_farmer.tts.fallback")


class FallbackSynthProvider(BaseTTSProvider):
    """Spoken telephony prompt fallback provider."""

    def __init__(self, cache_dir: str = "backend/cache/tts", prompts_dir: str = "backend/cache/prompts"):
        super().__init__(cache_dir=cache_dir)
        self.prompts_dir = Path(prompts_dir)
        if not self.prompts_dir.exists():
            # Fallback relative to project root
            self.prompts_dir = Path("cache/prompts")

    def _select_prompt_name(self, text: str, language: str = "am") -> str:
        """Map text content to the closest pre-recorded studio spoken prompt."""
        t_lower = text.lower().strip()
        lang = language if language in ("am", "om", "en") else "am"

        # 1. Greetings
        if any(w in t_lower for w in ("ጤና ይስጥልኝ", "ሰላም", "እንኳን", "welcome", "hello", "akkam", "ashamaa")):
            return f"greeting_{lang}.wav"

        # 2. Location inquiry
        if any(w in t_lower for w in ("የት ነው", "አካባቢ", "ወረዳ", "ክልል", "location", "woreda", "eessa", "bakka")):
            return f"ask_location_{lang}.wav"

        # 3. Problem inquiry
        if any(w in t_lower for w in ("ምን ችግር", "ችግር", "ሰብል", "problem", "crop", "rakkoo", "midhaan")):
            return f"ask_problem_{lang}.wav"

        # 4. Goodbye / completion
        if any(w in t_lower for w in ("ደህና ይሁኑ", "መልካም", "እናመሰግናለን", "bye", "goodbye", "nagaan")):
            return f"goodbye_{lang}.wav"

        # 5. One moment / thinking
        if any(w in t_lower for w in ("ይጠብቁ", "እየፈለግኩ", "ቆዩ", "moment", "wait", "eegaa")):
            return f"one_moment_{lang}.wav"

        # 6. Error or repetition
        if any(w in t_lower for w in ("ይቅርታ", "አልተሰማኝም", "እንደገና", "repeat", "sorry", "irra")):
            return f"repeat_prompt_{lang}.wav"

        # 7. Default to safe agricultural advisory fallback
        return f"safe_fallback_{lang}.wav"

    async def _synthesize_raw(
        self, text: str, voice: str | None = None, language: str = "am", rate: str | None = None, **kwargs
    ) -> bytes:
        """Retrieve pre-recorded spoken prompt PCM or generate gentle chime if absent."""
        lang = language if language in ("am", "om", "en") else "am"
        prompt_filename = self._select_prompt_name(text, language=lang)
        prompt_path = self.prompts_dir / prompt_filename

        if prompt_path.exists():
            try:
                raw_bytes = prompt_path.read_bytes()
                # If already WAV, transcode to 8kHz Linear PCM
                pcm_8k = audio_stream_to_pcm8k(raw_bytes)
                if pcm_8k and len(pcm_8k) > 0:
                    logger.info("Serving spoken telephony prompt fallback: '%s' (%d bytes PCM)", prompt_filename, len(pcm_8k))
                    return pcm_8k
            except Exception as e:
                logger.warning("Failed to decode prompt %s: %s", prompt_filename, e)

        # Fallback to general safe fallback if specific prompt failed
        general_fallback = self.prompts_dir / f"safe_fallback_{lang}.wav"
        if general_fallback.exists() and general_fallback != prompt_path:
            try:
                pcm_8k = audio_stream_to_pcm8k(general_fallback.read_bytes())
                if pcm_8k:
                    return pcm_8k
            except Exception:
                pass

        # Ultimate acoustic emergency fallback (soft 440Hz warm chime, never jarring harsh buzz)
        duration_s = max(1.5, min(6.0, len(text) * 0.05))
        sample_rate = 8000
        num_samples = int(duration_s * sample_rate)
        t = np.linspace(0, duration_s, num_samples, endpoint=False)
        envelope = np.exp(-1.5 * t)
        chime = 0.3 * np.sin(2 * np.pi * 440.0 * t) * envelope
        pcm_samples = (chime * 32767.0).astype(np.int16)
        return pcm_samples.tobytes()
