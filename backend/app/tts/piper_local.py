"""Local Neural Text-to-Speech (TTS) Provider powered by Piper ONNX.

High-performance, offline-capable neural speech synthesis with native support
for Amharic and regional languages. Automatically converts synthesized audio
into 8 kHz 16-bit signed linear mono PCM for Asterisk AudioSocket telephony streaming.
"""
import io
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

try:
    from app.audio.convert import audio_stream_to_pcm8k, pcm16k_to_pcm8k
    from app.config import settings
    from app.tts.base import BaseTTSProvider
    from app.tts.fallback_synth import FallbackSynthProvider
    from app.tts.normalizer import normalize_text_for_tts
except ImportError:
    from backend.app.audio.convert import audio_stream_to_pcm8k, pcm16k_to_pcm8k
    from backend.app.config import settings
    from backend.app.tts.base import BaseTTSProvider
    from backend.app.tts.fallback_synth import FallbackSynthProvider
    from backend.app.tts.normalizer import normalize_text_for_tts

logger = logging.getLogger("hello_farmer.tts.piper")


class PiperLocalTTSProvider(BaseTTSProvider):
    """Local Piper ONNX neural TTS synthesizer."""

    def __init__(
        self,
        cache_dir: str = "backend/cache/tts",
        model_path: str | Path | None = None,
        config_path: str | Path | None = None,
    ):
        super().__init__(cache_dir=cache_dir)
        self.models_dir = Path("backend/models/tts/piper")
        self.model_path = Path(model_path) if model_path else self._find_model("am")
        self.config_path = Path(config_path) if config_path else (
            Path(str(self.model_path) + ".json") if self.model_path else None
        )
        self.fallback_synth = FallbackSynthProvider(cache_dir=cache_dir)

    def _find_model(self, language: str) -> Optional[Path]:
        """Search for local ONNX model checkpoint for target language."""
        candidates = [
            self.models_dir / f"{language}_ET-medium.onnx",
            self.models_dir / f"{language}-medium.onnx",
            self.models_dir / f"{language}.onnx",
            Path(f"cache/models/{language}.onnx"),
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return p
        return None

    def is_model_available(self) -> bool:
        """Check if Piper model checkpoint and runtime are available."""
        if self.model_path and self.model_path.exists():
            return True
        return False

    async def _synthesize_raw(
        self,
        text: str,
        voice: str | None = None,
        language: str = "am",
        rate: str | None = None,
        **kwargs,
    ) -> bytes:
        """Synthesize text via local Piper neural model or spoken prompt fallback."""
        t0 = time.perf_counter()
        norm_text = normalize_text_for_tts(text, language=language) or text

        # Check for model checkpoint
        target_model = self.model_path or self._find_model(language)

        piper_executable = shutil.which("piper") or shutil.which("piper-tts")

        if target_model and target_model.exists() and piper_executable:
            try:
                cmd = [
                    piper_executable,
                    "--model", str(target_model),
                    "--output_raw",
                ]
                if self.config_path and self.config_path.exists():
                    cmd.extend(["--config", str(self.config_path)])

                proc = subprocess.run(
                    cmd,
                    input=norm_text.encode("utf-8"),
                    capture_output=True,
                    check=True,
                    timeout=10.0,
                )
                raw_pcm = proc.stdout
                if raw_pcm and len(raw_pcm) > 0:
                    # Piper typically outputs 16kHz or 22.05kHz 16-bit mono PCM.
                    pcm_8k = audio_stream_to_pcm8k(raw_pcm) or pcm16k_to_pcm8k(raw_pcm)
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    logger.info("Piper TTS synthesized %d bytes in %.1fms for '%s'", len(pcm_8k), latency_ms, text[:25])
                    return pcm_8k
            except Exception as e:
                logger.warning("Piper local synthesis execution failed: %s. Using spoken prompt fallback.", e)

        # Fallback to spoken telephony prompts (never return acoustic sine beeps)
        return await self.fallback_synth._synthesize_raw(text, voice=voice, language=language, rate=rate)
