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


logger = logging.getLogger("hello_farmer.stt.gemini")


class GeminiSTTProvider(BaseSTTProvider):
    def __init__(self, api_key: str | None = None, model_name: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name
        self._is_configured = False

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                genai.configure(api_key=self.api_key)
                self._is_configured = True
            except Exception as e:
                logger.warning(f"Could not configure Google Generative AI client: {e}")

    def _prepare_audio(self, wav_path_or_bytes: str | bytes) -> bytes:
        """Preprocess audio with AGC, pre-emphasis, and 16kHz WAV packaging."""
        if isinstance(wav_path_or_bytes, str):
            with open(wav_path_or_bytes, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(wav_path_or_bytes, bytes):
            raw_bytes = wav_path_or_bytes
        else:
            return b""
        return preprocess_speech_for_stt(raw_bytes, is_8k_pcm=not raw_bytes.startswith(b"RIFF"))

    async def transcribe(self, wav_path_or_bytes: str | bytes, language: str = "am") -> Transcript:
        """Transcribe audio using Google Gemini multimodal audio transcription."""
        start_time = time.perf_counter()
        lang_name = "Amharic (አማርኛ in Ge'ez script)" if language == "am" else "Afaan Oromo (in Latin Qubee script)"

        audio_data = self._prepare_audio(wav_path_or_bytes)

        if not self._is_configured or not audio_data:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return Transcript(
                text="",
                confidence=0.0,
                provider="gemini_unconfigured",
                latency_ms=latency_ms,
                language=language,
            )

        domain_bias = get_stt_biasing_prompt(language)
        prompt = (
            f"You are a specialized speech-to-text transcriber for {lang_name} spoken by Ethiopian farmers over telephone.\n"
            f"Agricultural domain context and common terms: {domain_bias}\n"
            "Listen carefully to this audio recording and transcribe verbatim exactly what was spoken.\n"
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

