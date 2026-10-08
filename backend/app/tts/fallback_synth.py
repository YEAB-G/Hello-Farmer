"""Deterministic Fallback Audio Synthesizer Provider.

Provides an offline secondary TTS provider selectable by config.
Generates modulated acoustic speech-band audio cues (8 kHz 16-bit mono linear PCM)
so the system never goes silent or crashes during offline testing or network drops.
"""

import numpy as np

try:
    from app.tts.base import BaseTTSProvider
except ImportError:
    from backend.app.tts.base import BaseTTSProvider


class FallbackSynthProvider(BaseTTSProvider):
    """Secondary offline acoustic synthesizer."""

    def __init__(self, cache_dir: str = "backend/cache/tts"):
        super().__init__(cache_dir=cache_dir)

    async def _synthesize_raw(self, text: str, voice: str | None = None, language: str = "am") -> bytes:
        """Synthesize modulated 8 kHz audio signal proportional to text syllable count."""
        # Estimate duration: ~80ms per character with a floor of 1.5s and cap of 10s
        duration_s = max(1.5, min(10.0, len(text) * 0.08))
        sample_rate = 8000
        num_samples = int(duration_s * sample_rate)
        t = np.linspace(0, duration_s, num_samples, endpoint=False)

        # Formant frequencies for speech presence (F1=500Hz, F2=1500Hz)
        base_f1 = 450.0 if language == "am" else 480.0
        base_f2 = 1450.0

        # Modulate amplitude with speech envelope (2-4 Hz syllable rhythm)
        envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 3.5 * t))
        audio = envelope * (0.4 * np.sin(2 * np.pi * base_f1 * t) + 0.2 * np.sin(2 * np.pi * base_f2 * t))
        audio = np.clip(audio, -1.0, 1.0)
        pcm_samples = (audio * 32767.0).astype(np.int16)
        return pcm_samples.tobytes()
