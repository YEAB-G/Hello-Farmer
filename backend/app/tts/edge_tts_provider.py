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

    DEFAULT_AMHARIC_VOICE = "am-ET-MekdesNeural"
    DEFAULT_OROMO_VOICE = "am-ET-MekdesNeural"  # Fallback: edge-tts lacks native om-ET voice

    def __init__(self, cache_dir: str = "backend/cache/tts"):
        super().__init__(cache_dir=cache_dir)

    async def _synthesize_google(self, text: str, language: str = "am") -> bytes:
        """Synthesize speech using Google Translate TTS API as resilient fallback."""
        try:
            import re
            import urllib.parse
            import httpx

            # Google TTS supports 'am' (Amharic) and 'en'.
            g_lang = "am" if language in ("am", "om") else "en"

            # Split into chunks of max 120 chars at punctuation boundaries
            parts = re.split(r'([።\n.!?])', text)
            chunks = []
            curr = ""
            for p in parts:
                if len(curr) + len(p) <= 120:
                    curr += p
                else:
                    if curr.strip():
                        chunks.append(curr.strip())
                    curr = p
            if curr.strip():
                chunks.append(curr.strip())

            combined_mp3 = bytearray()
            async with httpx.AsyncClient(timeout=10.0) as client:
                for chunk in chunks:
                    if not chunk.strip():
                        continue
                    url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(chunk)}&tl={g_lang}&client=tw-ob"
                    resp = await client.get(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                    )
                    if resp.status_code == 200 and resp.content:
                        combined_mp3.extend(resp.content)

            if combined_mp3:
                pcm_8k = audio_stream_to_pcm8k(bytes(combined_mp3))
                if pcm_8k and len(pcm_8k) > 0:
                    logger.info(f"Successfully synthesized {len(pcm_8k)} bytes PCM audio via Google TTS fallback for '{text[:25]}...'")
                    return pcm_8k
        except Exception as e:
            logger.error(f"Google TTS fallback error: {e}")
        return b""


    async def _synthesize_raw(self, text: str, voice: str | None = None, language: str = "am") -> bytes:
        """Synthesize text via edge-tts and transcode to 8 kHz linear PCM."""
        selected_voice = (
            voice if (voice and voice != "default")
            else (self.DEFAULT_AMHARIC_VOICE if language == "am" else self.DEFAULT_OROMO_VOICE)
        )

        try:
            communicate = edge_tts.Communicate(text, selected_voice, rate="-4%")
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
