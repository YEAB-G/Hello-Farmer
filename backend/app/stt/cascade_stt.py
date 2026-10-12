"""Smart STT Cascade with Fallback Arbitration.

Implements multi-engine STT fallback:
1. Primary: Groq Whisper (ultra-fast ~300ms inference).
2. Arbitration: Evaluates confidence, non-emptiness, and hallucination loops.
3. Fallback: Cascades to Gemini Flash Lite (deep contextual Amharic semantics).
4. Offline: Cascades to Local Faster-Whisper if internet/cloud connectivity drops.
"""
import logging
import time

try:
    from app.config import settings
    from app.stt.base import BaseSTTProvider, Transcript
    from app.stt.gemini_stt import GeminiSTTProvider
    from app.stt.groq_stt import GroqSTTProvider
    from app.stt.whisper_local import WhisperLocalSTTProvider
except ImportError:
    from backend.app.config import settings
    from backend.app.stt.base import BaseSTTProvider, Transcript
    from backend.app.stt.gemini_stt import GeminiSTTProvider
    from backend.app.stt.groq_stt import GroqSTTProvider
    from backend.app.stt.whisper_local import WhisperLocalSTTProvider

logger = logging.getLogger("hello_farmer.stt.cascade")


class CascadingSTTProvider(BaseSTTProvider):
    """Smart Cascading STT with latency-first fallback arbitration."""

    def __init__(
        self,
        primary: BaseSTTProvider | None = None,
        secondary: BaseSTTProvider | None = None,
        min_confidence_threshold: float = 0.60,
    ):
        self.min_confidence_threshold = min_confidence_threshold

        # Configure primary and secondary based on available API keys
        if primary is not None:
            self.primary = primary
        elif settings.GROQ_API_KEY:
            self.primary = GroqSTTProvider()
        elif settings.GEMINI_API_KEY:
            self.primary = GeminiSTTProvider()
        else:
            self.primary = WhisperLocalSTTProvider()

        if secondary is not None:
            self.secondary = secondary
        elif settings.GEMINI_API_KEY and isinstance(self.primary, GroqSTTProvider):
            self.secondary = GeminiSTTProvider()
        elif settings.GROQ_API_KEY and isinstance(self.primary, GeminiSTTProvider):
            self.secondary = GroqSTTProvider()
        else:
            self.secondary = WhisperLocalSTTProvider()

        self.offline_fallback = WhisperLocalSTTProvider()

    def _is_transcript_acceptable(self, transcript: Transcript) -> bool:
        """Arbitrate whether transcript meets confidence and quality criteria."""
        if not transcript or not transcript.text or not transcript.text.strip():
            return False

        if transcript.confidence < self.min_confidence_threshold:
            return False

        # Reject error/hallucination provider marks
        if "error" in transcript.provider or "hallucination" in transcript.provider:
            return False

        # Reject common English silence hallucinations
        english_artifacts = {"thank you for watching", "subtitles by", "amara.org", "you", "thanks"}
        if transcript.text.strip().lower() in english_artifacts:
            return False

        return True

    async def transcribe(self, wav_path_or_bytes: str | bytes, language: str = "am") -> Transcript:
        """Transcribe using fast primary engine, falling back to secondary on low confidence."""
        t0 = time.perf_counter()

        # Step 1: Attempt Primary Engine (e.g. Groq Whisper ~300ms)
        try:
            transcript = await self.primary.transcribe(wav_path_or_bytes, language=language)
            if self._is_transcript_acceptable(transcript):
                logger.info(
                    f"⚡ [STT FAST PATH] {transcript.provider} succeeded in {transcript.latency_ms:.1f}ms: '{transcript.text}'"
                )
                return transcript
            else:
                logger.warning(
                    f"⚠️ [STT ARBITRATION] {transcript.provider} produced low-confidence/empty result "
                    f"(conf={transcript.confidence:.2f}, text='{transcript.text}'). Cascading to secondary..."
                )
        except Exception as e:
            logger.warning(f"⚠️ [STT PRIMARY ERROR] {e}. Cascading to secondary provider...")

        # Step 2: Attempt Secondary Fallback Engine (e.g. Gemini Flash Lite)
        if self.secondary and self.secondary != self.primary:
            try:
                sec_transcript = await self.secondary.transcribe(wav_path_or_bytes, language=language)
                if self._is_transcript_acceptable(sec_transcript):
                    total_latency = (time.perf_counter() - t0) * 1000
                    logger.info(
                        f"🛡️ [STT CASCADE SUCCESS] Fallback to {sec_transcript.provider} succeeded in "
                        f"{total_latency:.1f}ms: '{sec_transcript.text}'"
                    )
                    sec_transcript.latency_ms = total_latency
                    return sec_transcript
            except Exception as e:
                logger.warning(f"⚠️ [STT SECONDARY ERROR] {e}. Cascading to offline local fallback...")

        # Step 3: Offline Local Whisper Fallback
        try:
            local_transcript = await self.offline_fallback.transcribe(wav_path_or_bytes, language=language)
            total_latency = (time.perf_counter() - t0) * 1000
            local_transcript.latency_ms = total_latency
            logger.info(f"🔄 [STT OFFLINE FALLBACK] Output: '{local_transcript.text}'")
            return local_transcript
        except Exception as e:
            total_latency = (time.perf_counter() - t0) * 1000
            logger.error(f"❌ [STT ALL FAILED] {e}")
            return Transcript(text="", confidence=0.0, provider="cascade_failed", latency_ms=total_latency, language=language)
