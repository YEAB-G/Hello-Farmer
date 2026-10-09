"""Google Gemini Audio Speech-to-Text (STT) Provider.

Transcribes telephony audio by passing 16 kHz WAV directly to Gemini Flash Lite.
Permissively licensed and SOTA for Ethiopian languages (Amharic and Afaan Oromo).
"""
import io
import logging
import time
import wave

import google.generativeai as genai

try:
    from app.audio.convert import pcm8k_to_pcm16k
    from app.config import settings
    from app.stt.base import BaseSTTProvider, Transcript
except ImportError:
    from backend.app.audio.convert import pcm8k_to_pcm16k
    from backend.app.config import settings
    from backend.app.stt.base import BaseSTTProvider, Transcript


logger = logging.getLogger("hello_farmer.stt.gemini")


class GeminiSTTProvider(BaseSTTProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name
        self._is_configured = False

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                genai.configure(api_key=self.api_key)
                self._is_configured = True
            except Exception as e:
                logger.warning(f"Could not configure Google Generative AI client: {e}")

    def _pcm_to_16k_wav(self, pcm_bytes: bytes) -> bytes:
        """Convert raw 8kHz mono PCM to 16kHz WAV bytes."""
        try:
            pcm_16k = pcm8k_to_pcm16k(pcm_bytes)
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

    async def transcribe(self, wav_path_or_bytes: str | bytes, language: str = "am") -> Transcript:
        """Transcribe audio using Google Gemini multimodal audio transcription."""
        start_time = time.perf_counter()
        lang_name = "Amharic (አማርኛ in Ge'ez script)" if language == "am" else "Afaan Oromo (in Latin Qubee script)"

        # Read or prepare WAV bytes
        if isinstance(wav_path_or_bytes, str):
            with open(wav_path_or_bytes, "rb") as f:
                audio_data = f.read()
        elif isinstance(wav_path_or_bytes, bytes):
            if wav_path_or_bytes.startswith(b"RIFF"):
                audio_data = wav_path_or_bytes
            else:
                audio_data = self._pcm_to_16k_wav(wav_path_or_bytes)
        else:
            audio_data = b""

        if not self._is_configured or not audio_data:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return Transcript(
                text="",
                confidence=0.0,
                provider="gemini_unconfigured",
                latency_ms=latency_ms,
                language=language,
            )

        prompt = (
            f"You are a specialized speech-to-text transcriber for {lang_name} spoken by Ethiopian farmers over telephone. "
            "Listen carefully to this audio recording and transcribe verbatim exactly what was spoken. "
            "Return ONLY the authentic transcription text with no introduction, no conversational filler, and no translation."
        )

        try:
            model = genai.GenerativeModel(self.model_name)
            response = await model.generate_content_async(
                [
                    prompt,
                    {
                        "mime_type": "audio/wav",
                        "data": audio_data,
                    },
                ]
            )
            raw_text = response.text.strip() if response.text else ""
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.info(f"Gemini STT ({self.model_name}) transcribed in {latency_ms:.1f}ms: '{raw_text}'")
            return Transcript(
                text=raw_text,
                confidence=0.95 if raw_text else 0.0,
                provider="gemini",
                latency_ms=latency_ms,
                language=language,
            )
        except Exception as e:
            logger.error(f"Gemini STT transcription error: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return Transcript(
                text="",
                confidence=0.0,
                provider="gemini_error",
                latency_ms=latency_ms,
                language=language,
            )

