"""Hugging Face Fine-Tuned Amharic ASR Provider (snapwre/hohe-asr-amharic).

Runs native CTC-based speech recognition using Wav2Vec2-BERT fine-tuned for Amharic.
Because CTC architectures predict character-level alignments directly, they are
completely immune to Whisper-style token hallucination loops and language confusion.

Modes:
1. High-Performance Local Offline Inference (via transformers & CPU PyTorch).
2. Serverless Cloud Fallback (via Hugging Face Inference Router).
"""
import asyncio
import io
import logging
import time
import wave
import numpy as np

try:
    from app.audio.convert import pcm8k_to_pcm16k
    from app.audio.preprocess import preprocess_speech_for_stt
    from app.config import settings
    from app.stt.base import BaseSTTProvider, Transcript
except ImportError:
    from backend.app.audio.convert import pcm8k_to_pcm16k
    from backend.app.audio.preprocess import preprocess_speech_for_stt
    from backend.app.config import settings
    from backend.app.stt.base import BaseSTTProvider, Transcript

logger = logging.getLogger("hello_farmer.stt.hf")


class HuggingFaceSTTProvider(BaseSTTProvider):
    """Amharic ASR provider powered by snapwre/hohe-asr-amharic."""

    _local_pipeline = None
    _pipeline_lock = asyncio.Lock()

    def __init__(
        self,
        token: str | None = None,
        model_id: str = "snapwre/hohe-asr-amharic",
    ):
        self.token = (
            token
            or getattr(settings, "HF_TOKEN", None)
            or getattr(settings, "HUGGINGFACE_API_KEY", None)
        )
        self.model_id = getattr(settings, "HF_ASR_MODEL", model_id)
        self.endpoints = [
            f"https://router.huggingface.co/hf-inference/models/{self.model_id}",
            f"https://api-inference.huggingface.co/models/{self.model_id}",
        ]

    def _prepare_wav(self, wav_path_or_bytes: str | bytes) -> bytes:
        """Preprocess audio with AGC and 16kHz WAV packaging."""
        if isinstance(wav_path_or_bytes, str):
            with open(wav_path_or_bytes, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(wav_path_or_bytes, bytes):
            raw_bytes = wav_path_or_bytes
        else:
            return b""
        return preprocess_speech_for_stt(raw_bytes, is_8k_pcm=not raw_bytes.startswith(b"RIFF"))

    def _get_local_pipeline(self):
        """Lazy-load transformers ASR pipeline for snapwre/hohe-asr-amharic."""
        if HuggingFaceSTTProvider._local_pipeline is None:
            try:
                from transformers import pipeline
                logger.info("Initializing local ASR pipeline for %s (device=cpu)...", self.model_id)
                HuggingFaceSTTProvider._local_pipeline = pipeline(
                    "automatic-speech-recognition",
                    model=self.model_id,
                    token=self.token,
                    device="cpu",
                )
                logger.info("Local ASR pipeline for %s initialized successfully!", self.model_id)
            except Exception as e:
                logger.warning("Could not initialize local transformers pipeline for %s: %s", self.model_id, e)
                return None
        return HuggingFaceSTTProvider._local_pipeline

    async def transcribe(
        self,
        wav_path_or_bytes: str | bytes,
        language: str = "am",
        **kwargs,
    ) -> Transcript:
        t0 = time.perf_counter()
        wav_bytes = self._prepare_wav(wav_path_or_bytes)
        if not wav_bytes or len(wav_bytes) < 800:
            return Transcript(text="", confidence=0.0, provider="hf_empty")

        # ----------------------------------------------------
        # Mode 1: Local Offline Inference (Zero Latency & Zero Quota)
        # ----------------------------------------------------
        pipeline_instance = self._get_local_pipeline()
        if pipeline_instance is not None:
            loop = asyncio.get_running_loop()
            try:
                def _run_inference():
                    # Pass raw 16kHz WAV bytes directly to CTC pipeline
                    out = pipeline_instance(wav_bytes)
                    res_text = ""
                    if isinstance(out, dict):
                        res_text = out.get("text", "").strip()
                    elif isinstance(out, list) and len(out) > 0:
                        res_text = out[0].get("text", "").strip()
                    else:
                        res_text = str(out).strip()
                    # Strip language tags like [AMH] or [amh] often emitted by multilingual CTC models
                    import re
                    res_text = re.sub(r"^\[\w+\]\s*", "", res_text)
                    return res_text.strip()

                text = await loop.run_in_executor(None, _run_inference)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                logger.info(
                    "Hohe Local ASR [%s] transcribed %d bytes in %.1fms: '%s'",
                    self.model_id,
                    len(wav_bytes),
                    latency_ms,
                    text,
                )
                return Transcript(
                    text=text,
                    confidence=0.95 if text else 0.0,
                    provider="hohe_local",
                    model=self.model_id,
                    latency_ms=latency_ms,
                    language=language,
                )
            except Exception as err:
                logger.error("Local Hohe ASR inference failed: %s, trying cloud fallback...", err)

        # ----------------------------------------------------
        # Mode 2: Cloud Inference Fallback
        # ----------------------------------------------------
        import httpx
        if not self.token:
            return Transcript(
                text="",
                confidence=0.0,
                provider="hf_unconfigured",
                error="HF_TOKEN missing",
                latency_ms=(time.perf_counter() - t0) * 1000.0,
            )

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "audio/wav",
            "x-wait-for-model": "true",
        }

        last_error = ""
        for endpoint in self.endpoints:
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(endpoint, headers=headers, content=wav_bytes)
                    if resp.status_code == 200:
                        result = resp.json()
                        text = result.get("text", "").strip() if isinstance(result, dict) else ""
                        latency_ms = (time.perf_counter() - t0) * 1000.0
                        return Transcript(
                            text=text,
                            confidence=0.92 if text else 0.0,
                            provider="hohe_cloud",
                            model=self.model_id,
                            latency_ms=latency_ms,
                            language=language,
                        )
                    else:
                        last_error = f"HTTP {resp.status_code}: {resp.text[:100]}"
            except Exception as e:
                last_error = str(e)

        # ----------------------------------------------------
        # Mode 3: Gemini / Groq STT Fallback
        # ----------------------------------------------------
        try:
            try:
                from app.stt.gemini_stt import GeminiSTTProvider
            except ImportError:
                from backend.app.stt.gemini_stt import GeminiSTTProvider
            gemini_fallback = GeminiSTTProvider()
            logger.info("Delegating to Gemini fast fallback STT for %s...", language)
            res = await gemini_fallback.transcribe(wav_bytes, language=language, **kwargs)
            if res.text and len(res.text.strip()) > 0:
                res.fallback_used = True
                return res
        except Exception as e:
            logger.warning("Gemini fallback STT error: %s", e)

        try:
            try:
                from app.stt.groq_stt import GroqSTTProvider
            except ImportError:
                from backend.app.stt.groq_stt import GroqSTTProvider
            groq_fallback = GroqSTTProvider()
            logger.info("Delegating to Groq fallback STT...")
            res = await groq_fallback.transcribe(wav_bytes, language=language, **kwargs)
            res.fallback_used = True
            return res
        except Exception as e:
            logger.error("Groq fallback failed: %s", e)

        return Transcript(
            text="",
            confidence=0.0,
            provider="hf_failed",
            error=last_error,
            latency_ms=(time.perf_counter() - t0) * 1000.0,
        )
