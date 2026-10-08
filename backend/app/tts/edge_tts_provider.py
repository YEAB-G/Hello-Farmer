"""Microsoft Edge TTS Provider (PROTOTYPE ONLY).

Provides natural neural text-to-speech for Amharic:
- Voices: 'am-ET-AmehaNeural' (Male), 'am-ET-MekdesNeural' (Female).
- Resamples output to 8 kHz 16-bit mono linear PCM for Asterisk telephony.
"""
import io
import logging

import edge_tts

try:
    from app.audio.convert import audio_stream_to_pcm8k
    from app.tts.base import BaseTTSProvider
except ImportError:
    from backend.app.audio.convert import audio_stream_to_pcm8k
    from backend.app.tts.base import BaseTTSProvider

logger = logging.getLogger("hello_farmer.tts.edge")


class EdgeTTSProvider(BaseTTSProvider):
    """Edge-TTS provider. Mark: PROTOTYPE ONLY."""

    DEFAULT_AMHARIC_VOICE = "am-ET-AmehaNeural"
    DEFAULT_OROMO_VOICE = "am-ET-AmehaNeural"  # Fallback: edge-tts lacks native om-ET voice

    def __init__(self, cache_dir: str = "backend/cache/tts"):
        super().__init__(cache_dir=cache_dir)

    async def _synthesize_raw(self, text: str, voice: str | None = None, language: str = "am") -> bytes:
        """Synthesize text via edge-tts and transcode to 8 kHz linear PCM."""
        selected_voice = (
            voice if (voice and voice != "default")
            else (self.DEFAULT_AMHARIC_VOICE if language == "am" else self.DEFAULT_OROMO_VOICE)
        )

        try:
            communicate = edge_tts.Communicate(text, selected_voice)
            mp3_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_buffer.write(chunk["data"])

            raw_mp3_bytes = mp3_buffer.getvalue()
            if not raw_mp3_bytes:
                return b""

            # Transcode MP3 stream to 8 kHz 16-bit signed linear mono PCM
            pcm_8k = audio_stream_to_pcm8k(raw_mp3_bytes)
            return pcm_8k
        except Exception as e:
            logger.error(f"Edge-TTS synthesis error for text '{text[:30]}...': {e}")
            return b""
