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
    from app.audio.preprocess import preprocess_speech_for_stt
    from app.config import settings
    from app.stt.base import BaseSTTProvider, Transcript
    from app.stt.prompts import get_stt_biasing_prompt
except ImportError:
    from backend.app.audio.convert import pcm8k_to_pcm16k
    from backend.app.audio.preprocess import preprocess_speech_for_stt
    from backend.app.config import settings
    from backend.app.stt.base import BaseSTTProvider, Transcript
    from backend.app.stt.prompts import get_stt_biasing_prompt

logger = logging.getLogger("hello_farmer.stt.groq")


class GroqSTTProvider(BaseSTTProvider):
    """Whisper speech-to-text powered by Groq cloud with acoustic pre-processing and domain biasing."""

    def __init__(self, api_key: str | None = None, model: str = "whisper-large-v3-turbo"):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model
        self.endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"

    def _prepare_wav(self, wav_path_or_bytes: str | bytes) -> bytes:
        """Preprocess audio with AGC, pre-emphasis, and 16kHz WAV packaging."""
        if isinstance(wav_path_or_bytes, str):
            with open(wav_path_or_bytes, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(wav_path_or_bytes, bytes):
            raw_bytes = wav_path_or_bytes
        else:
            return b""
        return preprocess_speech_for_stt(raw_bytes, is_8k_pcm=not raw_bytes.startswith(b"RIFF"))

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
        # Common English Whisper silence hallucinations
        english_hallucinations = ["thank you for watching", "subtitles by", "amara.org", "you"]
        if text.strip().lower() in english_hallucinations:
            return True
        return False

    async def transcribe(self, wav_path_or_bytes: str | bytes, language: str = "am") -> Transcript:
        t0 = time.perf_counter()
        if not self.api_key:
            logger.warning("GROQ_API_KEY not configured for STT.")
            return Transcript(text="", confidence=0.0, provider="groq_error")

        wav_bytes = self._prepare_wav(wav_path_or_bytes)
        if not wav_bytes:
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
            "prompt": get_stt_biasing_prompt(language),
        }
        if lang_code:
            data["language"] = lang_code

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

