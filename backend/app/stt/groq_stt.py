"""Groq Whisper STT Provider using whisper-large-v3-turbo."""
import io
import logging
import re
import time
import wave
import httpx
import numpy as np

try:
    from app.audio.convert import pcm8k_to_pcm16k
    from app.config import settings
    from app.stt.base import BaseSTTProvider, Transcript
except ImportError:
    from backend.app.audio.convert import pcm8k_to_pcm16k
    from backend.app.config import settings
    from backend.app.stt.base import BaseSTTProvider, Transcript

logger = logging.getLogger("hello_farmer.stt.groq")


class GroqSTTProvider(BaseSTTProvider):
    """Whisper speech-to-text powered by Groq cloud."""

    def __init__(self, api_key: str | None = None, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"

    def _pcm_to_16k_wav(self, pcm_bytes: bytes) -> bytes:
        """Convert raw 8kHz mono PCM to normalized 16kHz WAV bytes."""
        try:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            max_val = np.max(np.abs(samples)) if len(samples) > 0 else 0
            if max_val > 100:
                samples = samples * (24000.0 / max_val)
            normalized_pcm = np.clip(samples, -32768, 32767).astype(np.int16).tobytes()
            pcm_16k = pcm8k_to_pcm16k(normalized_pcm)
        except Exception:
            pcm_16k = pcm_bytes

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(pcm_16k)
        buf.seek(0)
        return buf.read()

    def _is_hallucination(self, text: str) -> bool:
        """Detect repetitive character/token looping common in low-resource Whisper outputs."""
        if not text:
            return True
        clean = re.sub(r"\s+", "", text)
        if len(clean) >= 4:
            # 3 or more of same character in a row e.g. ለለለ, ንንን, አአአ
            if re.search(r"(.)\1{2,}", clean):
                return True
            # Few distinct characters across string e.g. ለለልልል
            unique_chars = set(clean)
            if len(clean) >= 6 and len(unique_chars) <= 2:
                return True
        return False

    async def transcribe(self, wav_path_or_bytes: str | bytes, language: str = "am") -> Transcript:
        t0 = time.perf_counter()
        if not self.api_key:
            logger.warning("GROQ_API_KEY not configured for STT.")
            return Transcript(text="", confidence=0.0, provider="groq_error")

        if isinstance(wav_path_or_bytes, str):
            with open(wav_path_or_bytes, "rb") as f:
                wav_bytes = f.read()
        elif isinstance(wav_path_or_bytes, bytes):
            if wav_path_or_bytes.startswith(b"RIFF"):
                wav_bytes = wav_path_or_bytes
            else:
                wav_bytes = self._pcm_to_16k_wav(wav_path_or_bytes)
        else:
            return Transcript(text="", confidence=0.0, provider="groq_empty")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        files = {
            "file": ("speech.wav", wav_bytes, "audio/wav"),
        }
        lang_code = "am" if language == "am" else None
        data = {
            "model": self.model,
            "response_format": "json",
            "temperature": 0.0,
        }
        if lang_code:
            data["language"] = lang_code
            data["prompt"] = "የኢትዮጵያ ግብርና፣ በቆሎ፣ ስንዴ፣ ጤፍ፣ ማዳበሪያ፣ በሽታ፣ ዝናብ፣ እርሻ"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.endpoint, headers=headers, files=files, data=data)
                resp.raise_for_status()
                result = resp.json()
                text = result.get("text", "").strip()
                latency_ms = (time.perf_counter() - t0) * 1000

                # Filter hallucinated loops
                if self._is_hallucination(text):
                    logger.warning(f"Groq Whisper hallucination detected and suppressed: '{text}'")
                    return Transcript(
                        text="",
                        confidence=0.0,
                        provider="groq_whisper_hallucination",
                        latency_ms=latency_ms,
                        language=language,
                    )

                logger.info(f"Groq Whisper transcribed {len(wav_bytes)} bytes in {latency_ms:.1f}ms: '{text}'")
                return Transcript(
                    text=text,
                    confidence=0.90 if text else 0.0,
                    provider="groq_whisper",
                    latency_ms=latency_ms,
                    language=language,
                )
        except Exception as e:
            logger.error(f"Groq Whisper transcription failed: {e}")
            latency_ms = (time.perf_counter() - t0) * 1000
            return Transcript(
                text="",
                confidence=0.0,
                provider="groq_error",
                latency_ms=latency_ms,
                language=language,
            )

