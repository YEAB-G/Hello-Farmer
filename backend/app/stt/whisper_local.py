"""Local Faster-Whisper Speech-to-Text (STT) Provider.

Permissively licensed (MIT license) for commercial and offline operation.
"""
import io
import logging
import time

try:
    from app.stt.base import BaseSTTProvider, Transcript
except ImportError:
    from backend.app.stt.base import BaseSTTProvider, Transcript


logger = logging.getLogger("hello_farmer.stt.whisper")


class WhisperLocalSTTProvider(BaseSTTProvider):
    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ):
        try:
            from app.config import settings
            default_model = getattr(settings, "WHISPER_MODEL_SIZE", "tiny")
            default_device = getattr(settings, "WHISPER_DEVICE", "cpu")
        except ImportError:
            default_model = "tiny"
            default_device = "cpu"

        self.model_size = model_size or default_model
        self.device = device or default_device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.model = None

    def _load_model_if_needed(self):
        if getattr(self, "_force_uninitialized", False):
            return
        if self.model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(
                    "Loading faster-whisper model (%s) on %s with %s quantization...",
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=self.cpu_threads,
                )
            except Exception as e:
                logger.warning(f"Could not load faster-whisper model: {e}")

    async def transcribe(
        self,
        wav_path_or_bytes: str | bytes,
        language: str = "am",
        beam_size: int = 1,
        **kwargs,
    ) -> Transcript:
        """Transcribe speech using local faster-whisper model."""
        start_time = time.perf_counter()
        self._load_model_if_needed()

        if self.model is None:
            # Model unavailable or uninitialized - never return fake ASR transcripts (Rule 8)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return Transcript(
                text="",
                confidence=0.0,
                provider="whisper_local_unavailable",
                error="Faster-Whisper model is not initialized or unavailable on this system",
                latency_ms=max(1.0, latency_ms),
                language=language,
            )

        try:
            # Prepare audio source
            if isinstance(wav_path_or_bytes, bytes):
                audio_input = io.BytesIO(wav_path_or_bytes)
            else:
                audio_input = wav_path_or_bytes

            segments, info = self.model.transcribe(
                audio_input,
                language=language,
                beam_size=beam_size,
                vad_filter=True,
                **kwargs,
            )
            text = " ".join([segment.text for segment in segments]).strip()
            latency_ms = (time.perf_counter() - start_time) * 1000.0

            return Transcript(
                text=text,
                confidence=float(info.language_probability) if hasattr(info, "language_probability") else 0.85,
                provider="whisper_local",
                latency_ms=latency_ms,
                language=language,
            )
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return Transcript(
                text="",
                confidence=0.0,
                provider="whisper_error",
                error=str(e),
                latency_ms=latency_ms,
                language=language,
            )
