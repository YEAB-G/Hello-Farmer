"""Google Gemini Audio Speech-to-Text (STT) Provider.

Primary speech-to-text engine for Hello Farmer telephony and web voice pipelines.
Uses the modern Google GenAI SDK (gemini-3.5-transcribe / gemini-3.5-flash) with
domain biasing for Ethiopian smallholder farming vocabulary (Amharic & Afaan Oromo).

Features:
- Telephony-aware audio normalization (16 kHz WAV, AGC, pre-emphasis)
- Silence/noise energy gating (prevents wasted API calls on background noise)
- Native multimodal & dedicated audio transcription parsing
- Preservation of original language without unwanted English translation
- Bounded exponential backoff retry for transient 503 errors
- Resilient fallback delegation to Groq/Whisper when free-tier quotas (3 RPM) are exceeded
- Structured Transcript metadata (model, latency, provider, confidence)
"""
import asyncio
import io
import logging
import time
import wave
from typing import Optional

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

logger = logging.getLogger("hello_farmer.stt.gemini")


class GeminiSTTProvider(BaseSTTProvider):
    """Google Gemini STT provider with dedicated transcription and telephony fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        fallback_provider: Optional[BaseSTTProvider] = None,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)
        self.model_name = (
            model_name
            or getattr(settings, "GEMINI_STT_MODEL", None)
            or getattr(settings, "STT_GEMINI_MODEL", "gemini-3.5-flash-lite")
        )
        if self.model_name == "gemini-3.5-transcribe":
            self.model_name = "gemini-3.5-flash-lite"
        self._fallback_provider = fallback_provider
        self._genai_client = None
        self._legacy_genai = None
        self._is_configured = False

        self._init_client()

    def _init_client(self):
        """Initialize Google GenAI client (prefer modern google-genai, fallback to legacy)."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY not configured for Gemini STT provider.")
            return

        # 1. Try modern google-genai SDK
        try:
            from google import genai
            self._genai_client = genai.Client(api_key=self.api_key)
            self._is_configured = True
            logger.info("Initialized modern google-genai client for Gemini STT (%s)", self.model_name)
            return
        except ImportError:
            logger.debug("google-genai SDK not available, attempting google.generativeai fallback.")
        except Exception as e:
            logger.warning("Failed to initialize google-genai client: %s", e)

        # 2. Try legacy google.generativeai SDK
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=self.api_key)
            self._legacy_genai = legacy_genai
            self._is_configured = True
            logger.info("Initialized legacy google.generativeai for Gemini STT (%s)", self.model_name)
        except Exception as e:
            logger.error("Could not configure any Google Gemini client for STT: %s", e)

    def _get_fallback_provider(self) -> Optional[BaseSTTProvider]:
        """Lazy load configured fallback STT provider (or None if disabled)."""
        if self._fallback_provider is not None:
            return self._fallback_provider

        fallback_type = getattr(settings, "STT_FALLBACK_PROVIDER", "none").lower()
        if fallback_type in ("none", "null", "false", "disabled", "gemini"):
            return None

        try:
            if fallback_type == "groq" and getattr(settings, "GROQ_API_KEY", None):
                try:
                    from app.stt.groq_stt import GroqSTTProvider
                except ImportError:
                    from backend.app.stt.groq_stt import GroqSTTProvider
                self._fallback_provider = GroqSTTProvider()
            elif fallback_type == "whisper_local":
                try:
                    from app.stt.whisper_local import WhisperLocalSTTProvider
                except ImportError:
                    from backend.app.stt.whisper_local import WhisperLocalSTTProvider
                self._fallback_provider = WhisperLocalSTTProvider()
        except Exception as err:
            logger.warning("Could not initialize STT fallback provider '%s': %s", fallback_type, err)
        return self._fallback_provider

    def _prepare_audio(self, wav_path_or_bytes: str | bytes) -> tuple[bytes, float, float]:
        """Preprocess audio with AGC, pre-emphasis, and silence/duration detection.

        Returns:
            Tuple of (preprocessed_wav_16k_bytes, duration_seconds, rms_energy).
        """
        if isinstance(wav_path_or_bytes, str):
            try:
                with open(wav_path_or_bytes, "rb") as f:
                    raw_bytes = f.read()
            except Exception as e:
                logger.error("Failed to read audio file '%s': %s", wav_path_or_bytes, e)
                return b"", 0.0, 0.0
        elif isinstance(wav_path_or_bytes, bytes):
            raw_bytes = wav_path_or_bytes
        else:
            return b"", 0.0, 0.0

        if not raw_bytes or len(raw_bytes) < 32:
            return b"", 0.0, 0.0

        is_8k = not raw_bytes.startswith(b"RIFF")
        wav_16k = preprocess_speech_for_stt(raw_bytes, is_8k_pcm=is_8k)
        if not wav_16k or len(wav_16k) < 44:
            return b"", 0.0, 0.0

        duration_sec = 0.0
        rms_energy = 0.0
        try:
            with wave.open(io.BytesIO(wav_16k), "rb") as wf:
                framerate = wf.getframerate()
                nframes = wf.getnframes()
                duration_sec = nframes / float(framerate) if framerate > 0 else 0.0
                frames = wf.readframes(nframes)
                if frames:
                    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                    rms_energy = float(np.sqrt(np.mean(samples**2)))
        except Exception as e:
            logger.debug("Could not inspect audio stats: %s", e)

        return wav_16k, duration_sec, rms_energy

    async def transcribe(
        self,
        wav_path_or_bytes: str | bytes,
        language: str = "am",
        **kwargs,
    ) -> Transcript:
        """Transcribe farmer speech using Gemini API with bounded fallback."""
        start_time = time.perf_counter()
        raw_lang = (language or "am").lower().strip()
        context = kwargs.get("context")
        if raw_lang in ("om", "oromo", "afaan_oromo"):
            lang_code = "om"
            lang_name = "Afaan Oromo (using Latin Qubee script)"
            instruction = (
                f"Transcribe this speech accurately in original {lang_name}. "
                "Do NOT translate into English or add commentary. Return ONLY the transcription text verbatim."
            )
        elif raw_lang in ("ti", "tigrinya", "tigrigna"):
            lang_code = "ti"
            lang_name = "Tigrinya (ትግርኛ using Ge'ez Fidel script)"
            instruction = (
                f"Transcribe this speech accurately in original {lang_name}. "
                "Do NOT translate into English or add commentary. Return ONLY the transcription text verbatim."
            )
        elif raw_lang in ("so", "somali", "soomaali"):
            lang_code = "so"
            lang_name = "Somali (Af-Soomaali using Latin script)"
            instruction = (
                f"Transcribe this speech accurately in original {lang_name}. "
                "Do NOT translate into English or add commentary. Return ONLY the transcription text verbatim."
            )
        elif raw_lang in ("en", "english"):
            lang_code = "en"
            lang_name = "English"
            instruction = (
                "Transcribe this speech accurately in English. "
                "Return ONLY the transcription text verbatim."
            )
        elif raw_lang in ("auto", "detect"):
            lang_code = "auto"
            lang_name = "Ethiopian languages (Amharic, Afaan Oromo, Tigrinya, Somali, or English)"
            instruction = (
                "Identify the spoken language among Amharic, Afaan Oromo, Tigrinya, Somali, or English, "
                "and transcribe the speech verbatim in that language's native script. "
                "Do NOT translate into English. Return ONLY the transcribed text."
            )
        elif context == "location":
            lang_code = "am" if raw_lang not in ("om", "ti", "so", "en") else raw_lang
            instruction = (
                "You are an acoustic Speech-to-Text transcriber for an Ethiopian phone hotline. "
                "The caller is answering what city, woreda, or zone they are calling from (e.g. ባህር ዳር, አዳማ, ደብረ ብርሃን, ሀዋሳ, ጎንደር, ጅማ, መቀሌ, ባሌ, ወዘተ). "
                "Transcribe the EXACT location name spoken. Use Ge'ez Fidel script (or Latin if spoken in English/Oromo). "
                "CRITICAL RULES:\n"
                "- Transcribe what you hear phonetically verbatim. Do NOT guess or substitute another city from memory.\n"
                "- Return ONLY the transcribed location name."
            )
        else:
            lang_code = "am"
            lang_name = "Amharic (አማርኛ using Ethiopic Fidel script)"
            biasing = get_stt_biasing_prompt("am", context=context)
            instruction = (
                "You are an acoustic Speech-to-Text transcriber for a phone call hotline. "
                "Transcribe the spoken audio verbatim without translating or altering the meaning. "
                "If the caller speaks Amharic, transcribe into authentic Amharic Fidel script. "
                "If the caller speaks English (e.g. 'I have finished', 'I am done', 'Thank you', 'Goodbye'), transcribe verbatim in English. "
                f"Vocabulary biasing context: {biasing}, ጨርሻለሁ, ይበቃል, አመሰግናለሁ, በቃኝ, የለም, I have finished, I am done, that is all. "
                "CRITICAL RULES:\n"
                "- Transcribe ONLY the exact spoken words verbatim.\n"
                "- NEVER output 'ሄሎ' or 'ሰላም' unless the caller explicitly said 'hello' or 'ሰላም'.\n"
                "- If the caller speaks 'ጨርሻለሁ', transcribe it as 'ጨርሻለሁ'.\n"
                "- If the caller speaks 'I have finished', transcribe it as 'I have finished'.\n"
                "- If the audio is silence or background noise, output an empty string."
            )

        # Step 1: Preprocess and detect silence
        audio_data, duration_sec, rms = self._prepare_audio(wav_path_or_bytes)
        elapsed_prep = (time.perf_counter() - start_time) * 1000.0

        # Silence gating: short or near-silent utterances should not hit the Gemini API
        if not audio_data or duration_sec < 0.25 or rms < 0.003:
            logger.debug(
                "Audio is silence or too short (duration=%.2fs, rms=%.5f). Skipping Gemini STT call.",
                duration_sec,
                rms,
            )
            return Transcript(
                text="",
                confidence=0.0,
                provider="gemini_silence",
                model=self.model_name,
                latency_ms=elapsed_prep,
                language=lang_code,
                processing_duration_sec=duration_sec,
            )

        # Step 2: Verify provider configuration
        if not self._is_configured:
            logger.warning("Gemini STT is not configured. Falling back to alternative STT provider.")
            return await self._delegate_to_fallback(
                wav_path_or_bytes=wav_path_or_bytes,
                language=lang_code,
                error_reason="GEMINI_API_KEY_NOT_CONFIGURED",
                start_time=start_time,
            )

        # Step 4: Execute Gemini STT call with bounded retries and exponential backoff
        max_attempts = 3
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                raw_text, detected_lang = await self._call_gemini_api(instruction, audio_data)
                clean_text = raw_text.strip() if raw_text else ""

                if not clean_text:
                    logger.info("Gemini STT returned empty transcript for non-silent audio; delegating to fallback STT.")
                    return await self._delegate_to_fallback(
                        wav_path_or_bytes=wav_path_or_bytes,
                        language=lang_code,
                        error_reason="GEMINI_EMPTY_TRANSCRIPT",
                        start_time=start_time,
                    )

                total_latency = (time.perf_counter() - start_time) * 1000.0
                confidence = 0.95 if len(clean_text) > 2 else 0.0

                logger.info(
                    "Gemini STT [%s] transcribed (%d chars) in %.1fms: '%s'",
                    self.model_name,
                    len(clean_text),
                    total_latency,
                    clean_text,
                )

                return Transcript(
                    text=clean_text,
                    confidence=confidence,
                    provider="gemini",
                    model=self.model_name,
                    latency_ms=total_latency,
                    language=lang_code,
                    detected_language=detected_lang or lang_code,
                    processing_duration_sec=duration_sec,
                )

            except Exception as err:
                is_timeout = isinstance(err, (asyncio.TimeoutError, TimeoutError))
                last_error = "TimeoutError: Request exceeded deadline" if is_timeout else str(err)
                err_lower = last_error.lower()
                is_rate_limit = "429" in last_error or "quota" in err_lower or "resource_exhausted" in err_lower
                is_transient = is_timeout or "503" in last_error or "unavailable" in err_lower or "timeout" in err_lower

                logger.warning(
                    "Gemini STT attempt %d failed: %s (rate_limit=%s, transient=%s, timeout=%s)",
                    attempt,
                    last_error or err.__class__.__name__,
                    is_rate_limit,
                    is_transient,
                    is_timeout,
                )

                if is_rate_limit:
                    # Free tier quota exhausted (e.g. 3 RPM exceeded) -> do not block, cascade immediately
                    logger.info("Gemini STT quota limit reached. Cascading immediately to fallback provider.")
                    break

                if attempt < max_attempts and is_transient:
                    backoff_sec = 0.5 * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff_sec)
                    continue
                break

        # Step 5: Fallback delegation on error or quota exhaustion
        return await self._delegate_to_fallback(
            wav_path_or_bytes=wav_path_or_bytes,
            language=lang_code,
            error_reason=last_error or "Gemini API error",
            start_time=start_time,
        )

    async def _call_gemini_api(self, prompt: str, audio_bytes: bytes) -> tuple[str, Optional[str]]:
        """Call Gemini API using modern google-genai SDK or legacy fallback."""
        if self._genai_client:
            from google.genai import types

            loop = asyncio.get_running_loop()
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")

            # Try primary model, auto-resolving legacy names if needed
            model_to_use = self.model_name
            if model_to_use in ("gemini-flash-latest", "gemini-2.5-flash"):
                model_to_use = "gemini-3.5-transcribe"

            cfg = types.GenerateContentConfig(
                temperature=0.0,
            )

            def _sync_generate():
                return self._genai_client.models.generate_content(
                    model=model_to_use,
                    contents=[prompt, audio_part],
                    config=cfg,
                )

            stt_timeout = float(getattr(settings, "GEMINI_STT_TIMEOUT_SECONDS", getattr(settings, "GEMINI_TIMEOUT_SECONDS", 8.0)))
            response = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_generate),
                timeout=stt_timeout,
            )

            # Parse response parts
            transcript_text = ""
            detected_lang = None

            candidates = getattr(response, "candidates", []) or []
            if candidates:
                parts = getattr(candidates[0].content, "parts", []) or []
                for pt in parts:
                    # Check for dedicated audio_transcription attribute (gemini-3.5-transcribe)
                    at = getattr(pt, "audio_transcription", None)
                    if at is not None:
                        if hasattr(at, "text") and at.text:
                            transcript_text += at.text + " "
                        if hasattr(at, "language_code") and at.language_code:
                            detected_lang = at.language_code
                    # Check for regular text attribute
                    txt = getattr(pt, "text", None)
                    if txt:
                        transcript_text += txt + " "

            if not transcript_text and hasattr(response, "text") and response.text:
                transcript_text = response.text

            return transcript_text.strip(), detected_lang

        elif self._legacy_genai:
            model = self._legacy_genai.GenerativeModel(self.model_name)
            response = await asyncio.wait_for(
                model.generate_content_async(
                    [
                        prompt,
                        {
                            "mime_type": "audio/wav",
                            "data": audio_bytes,
                        },
                    ]
                ),
                timeout=getattr(settings, "GEMINI_TIMEOUT_SECONDS", 12.0),
            )
            raw = response.text.strip() if response and response.text else ""
            return raw, None

        raise RuntimeError("No configured Google Gemini client is available.")

    async def _delegate_to_fallback(
        self,
        wav_path_or_bytes: str | bytes,
        language: str,
        error_reason: str,
        start_time: float,
    ) -> Transcript:
        """Seamlessly delegate transcription to the configured fallback STT provider."""
        fallback = self._get_fallback_provider()
        if fallback:
            try:
                logger.info(
                    "Switching STT provider from Gemini to %s due to: %s",
                    fallback.__class__.__name__,
                    error_reason,
                )
                fb_transcript = await fallback.transcribe(wav_path_or_bytes, language=language)

                # If primary fallback produced empty text (e.g. unsupported Oromo in Whisper cloud), cascade to local Whisper
                if not fb_transcript.text:
                    try:
                        try:
                            from app.stt.whisper_local import WhisperLocalSTTProvider
                        except ImportError:
                            from backend.app.stt.whisper_local import WhisperLocalSTTProvider
                        offline_whisper = WhisperLocalSTTProvider()
                        fb_transcript = await offline_whisper.transcribe(wav_path_or_bytes, language=language)
                    except Exception as off_err:
                        logger.debug("Offline Whisper cascade failed: %s", off_err)

                total_latency = (time.perf_counter() - start_time) * 1000.0

                return Transcript(
                    text=fb_transcript.text,
                    confidence=fb_transcript.confidence,
                    provider=fb_transcript.provider,
                    model=getattr(fb_transcript, "model", None) or "fallback_stt",
                    latency_ms=total_latency,
                    language=language,
                    detected_language=getattr(fb_transcript, "detected_language", language),
                    fallback_used=True,
                    error=f"Gemini STT failed: {error_reason}",
                    processing_duration_sec=getattr(fb_transcript, "processing_duration_sec", None),
                )
            except Exception as fb_err:
                logger.error("Fallback STT provider also failed: %s", fb_err)

        total_latency = (time.perf_counter() - start_time) * 1000.0
        return Transcript(
            text="",
            confidence=0.0,
            provider="gemini_failed",
            model=self.model_name,
            latency_ms=total_latency,
            language=language,
            fallback_used=True,
            error=f"All STT providers failed. Last error: {error_reason}",
        )
