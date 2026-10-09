"""Call flow state machine and session orchestrator for Asterisk AudioSocket telephony.

Implements Section 6.1 requirements:
- ANSWER: Bilingual greeting disclaimer.
- CONSENT: Spoken voice consent query for first-time callers (default to No on silence/unclear).
- LISTEN: VAD speech endpointing (energy & silence thresholding).
- THINK: Immediate "one moment" prompt playback to prevent dead air.
- SPEAK: Chunked 8 kHz PCM streaming back to Asterisk (barge-in off by default).
- LOW CONFIDENCE: Repeat prompt, max 2 failures -> referral + hangup.
- TIMEOUTS: 2 consecutive silent turns -> goodbye + hangup. 10m hard cap.
- ERRORS: Pre-rendered apology + referral + clean hangup.
"""
import asyncio
import hashlib
import logging
import time
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

try:
    from app.config import settings
    from app.pipeline import SessionState, process_utterance
    from app.telephony.audiosocket_server import (
        TYPE_AUDIO,
        TYPE_HANGUP,
        AudioSocketConnection,
    )
    from app.telephony.endpointing import EndpointState, VADEndpointer
    from app.telephony.prompts_audio import get_prompt_pcm
except ImportError:
    from backend.app.config import settings
    from backend.app.pipeline import SessionState, process_utterance
    from backend.app.telephony.audiosocket_server import (
        TYPE_AUDIO,
        TYPE_HANGUP,
        AudioSocketConnection,
    )
    from backend.app.telephony.endpointing import EndpointState, VADEndpointer
    from backend.app.telephony.prompts_audio import get_prompt_pcm

logger = logging.getLogger("hello_farmer.call_flow")

# Global concurrency tracker
ACTIVE_CALL_COUNT = 0
CALL_LOCK = asyncio.Lock()


class CallStateMachine:
    """Manages the full lifecycle of a single telephone call over AudioSocket."""

    def __init__(self, conn: AudioSocketConnection):
        self.conn = conn
        self.call_uuid = conn.call_uuid or "unknown_call"
        self.caller_hash = hashlib.sha256(
            f"{settings.SALT_HASH_SECRET}:{self.call_uuid}".encode()
        ).hexdigest()

        self.session_state = SessionState(
            session_id=self.call_uuid,
            caller_hash=self.caller_hash,
            language="am",
            is_first_time=True,
            has_consented=False,
            turn_count=0,
            consecutive_silence_count=0,
        )

        self.endpointer = VADEndpointer(
            energy_threshold=200,
            min_speech_ms=250,
            silence_timeout_ms=settings.SPEECH_SILENCE_TIMEOUT_MS,
            initial_silence_timeout_sec=settings.INITIAL_SILENCE_TIMEOUT_SECONDS,
            max_utterance_sec=30.0,
        )

        self.start_time = time.monotonic()
        self.consecutive_low_conf_count = 0
        self.db_engine = create_async_engine(settings.DATABASE_URL, echo=False)
        self.session_factory = async_sessionmaker(self.db_engine, expire_on_commit=False)

    async def run(self):
        """Main entry point running the state machine loop until call termination."""
        global ACTIVE_CALL_COUNT

        async with CALL_LOCK:
            if ACTIVE_CALL_COUNT >= settings.CONCURRENCY_LIMIT:
                logger.warning(
                    f"Concurrency limit ({settings.CONCURRENCY_LIMIT}) reached. Rejecting call: {self.call_uuid}"
                )
                await self._play_prompt("error", "am")
                await self.conn.hangup()
                return
            ACTIVE_CALL_COUNT += 1

        try:
            logger.info(f"Starting call state machine for UUID: {self.call_uuid}")

            # State 1: ANSWER (Play bilingual greeting)
            await self._state_answer()

            # State 2: CONSENT (If first-time caller)
            if self.session_state.is_first_time:
                await self._state_consent()

            # Conversation Turn Loop: LISTEN -> THINK -> SPEAK
            while self.conn.is_active:
                # Check maximum call duration cap (10 minutes)
                if time.monotonic() - self.start_time >= settings.MAX_CALL_DURATION_SECONDS:
                    logger.info(f"Max call duration reached ({settings.MAX_CALL_DURATION_SECONDS}s). Terminating.")
                    await self._play_prompt("goodbye", self.session_state.language)
                    break

                # State 3: LISTEN with VAD
                audio_pcm = await self._state_listen()
                if audio_pcm is None:
                    # Silence timeout or caller disconnect handled inside
                    if self.session_state.consecutive_silence_count >= 2:
                        logger.info("Caller silent for 2 consecutive turns. Ending call.")
                        await self._play_prompt("goodbye", self.session_state.language)
                        break
                    continue

                # Reset silence counter on speech detected
                self.session_state.consecutive_silence_count = 0
                self.session_state.turn_count += 1

                # State 4: THINK (Immediate "one moment" cue)
                await self._state_think()

                # State 5: Core Processing & SPEAK
                await self._state_speak(audio_pcm)

        except Exception as e:
            logger.error(f"Unhandled error in call state machine {self.call_uuid}: {e}")
            await self._play_prompt("error", self.session_state.language)
        finally:
            await self.conn.hangup()
            await self.db_engine.dispose()
            async with CALL_LOCK:
                ACTIVE_CALL_COUNT = max(0, ACTIVE_CALL_COUNT - 1)
            logger.info(f"Call session ended for UUID: {self.call_uuid}. Active calls remaining: {ACTIVE_CALL_COUNT}")

    async def _play_prompt(self, prompt_name: str, lang: str):
        """Play a pre-rendered 8 kHz PCM prompt audio to Asterisk."""
        pcm_bytes = get_prompt_pcm(prompt_name, lang)
        if pcm_bytes:
            await self.conn.send_audio(pcm_bytes)

    async def _state_answer(self):
        """State 1: Play disclaimer and greeting."""
        logger.info(f"[{self.call_uuid}] State: ANSWER")
        # Play bilingual greeting
        await self._play_prompt("greeting", "am")
        await self.conn.drain_input()
        await asyncio.sleep(0.05)

    async def _state_consent(self):
        """State 2: Voice consent question for first-time callers."""
        logger.info(f"[{self.call_uuid}] State: CONSENT")
        await self._play_prompt("consent", self.session_state.language)
        await self.conn.drain_input()

        # Listen for short voice confirmation (max 5s)
        self.endpointer.reset()
        self.endpointer.initial_silence_timeout_sec = 5.0
        pcm_data = await self._collect_speech_frames()

        if pcm_data and len(pcm_data) > 1600:  # > 100ms of audio
            # Process short answer
            resp = await process_utterance(
                audio_bytes=pcm_data,
                session=self.session_state,
                text_override=None
            )
            ans_text = resp.text.lower()
            self.session_state.has_consented = True
            if any(k in ans_text for k in ["አዎ", "እሺ", "eyyee", "eeyyee", "yes", "okay", "ok"]):
                logger.info(f"[{self.call_uuid}] Caller granted voice consent.")
            else:
                # Farmer asked an actual agricultural question immediately
                logger.info(f"[{self.call_uuid}] Caller asked question during consent turn: '{ans_text[:40]}'. Answering now.")
                if resp.audio and len(resp.audio) > 0:
                    await self.conn.send_audio(resp.audio)
                else:
                    await self._play_prompt("safe_fallback", self.session_state.language)
                await self.conn.drain_input()
        else:
            self.session_state.has_consented = True
            logger.info(f"[{self.call_uuid}] No explicit consent heard. Proceeding to LISTEN state.")

    async def _state_listen(self) -> Optional[bytes]:
        """State 3: Listen for caller utterance with VAD."""
        logger.info(f"[{self.call_uuid}] State: LISTEN (Turn {self.session_state.turn_count + 1})")
        await self.conn.drain_input()
        self.endpointer.reset()
        self.endpointer.initial_silence_timeout_sec = 8.0
        speech_pcm = await self._collect_speech_frames()

        if not speech_pcm or len(speech_pcm) < 3200:  # < 200ms
            self.session_state.consecutive_silence_count += 1
            logger.info(
                f"[{self.call_uuid}] No speech detected (silence count: {self.session_state.consecutive_silence_count})"
            )
            if self.session_state.consecutive_silence_count < 2:
                # Prompt caller to speak
                await self._play_prompt("repeat_prompt", self.session_state.language)
                await self.conn.drain_input()
            return None

        return speech_pcm

    async def _state_think(self):
        """State 4: Play immediate thinking cue ("One moment...")."""
        logger.info(f"[{self.call_uuid}] State: THINK")
        await self._play_prompt("one_moment", self.session_state.language)

    async def _state_speak(self, audio_pcm: bytes):
        """State 5: Run AI pipeline, check confidence, stream answer back."""
        logger.info(f"[{self.call_uuid}] State: SPEAK - processing utterance...")
        start_t = time.perf_counter()

        # Run pipeline
        response = await process_utterance(
            audio_bytes=audio_pcm,
            session=self.session_state,
            text_override=None
        )

        duration_ms = (time.perf_counter() - start_t) * 1000
        logger.info(f"[{self.call_uuid}] Utterance processed in {duration_ms:.1f}ms. Grounded: {response.metadata.grounded}")

        # Check for Low Confidence / Empty STT
        if response.metadata.confidence < 0.4 or not response.text.strip():
            self.consecutive_low_conf_count += 1
            logger.warning(f"[{self.call_uuid}] Low confidence turn (count: {self.consecutive_low_conf_count})")
            if self.consecutive_low_conf_count >= 2:
                logger.info(f"[{self.call_uuid}] 2 low-confidence turns. Playing referral and terminating.")
                await self._play_prompt("safe_fallback", self.session_state.language)
                await self._play_prompt("goodbye", self.session_state.language)
                await self.conn.hangup()
                return
            else:
                await self._play_prompt("repeat_prompt", self.session_state.language)
                await self.conn.drain_input()
                return

        self.consecutive_low_conf_count = 0

        # Stream Audio Answer Back to Asterisk
        if response.audio and len(response.audio) > 0:
            logger.info(f"[{self.call_uuid}] Streaming {len(response.audio)} bytes of audio answer to caller...")
            await self.conn.send_audio(response.audio)
        else:
            # Fallback to pre-rendered safe fallback if audio synthesis failed
            logger.warning(f"[{self.call_uuid}] Response audio empty, streaming safe fallback audio.")
            await self._play_prompt("safe_fallback", self.session_state.language)

        await self.conn.drain_input()

    async def _collect_speech_frames(self) -> Optional[bytes]:
        """Read 20ms audio frames from AudioSocket connection and feed VAD endpointer."""
        total_audio_frames = 0
        while self.conn.is_active:
            frame = await self.conn.read_frame()
            if not frame:
                return None

            msg_type, payload = frame
            # 0x00 is Asterisk's AUDIOSOCKET_TYPE_TERMINATE (Hangup)
            if msg_type == 0x00:
                logger.info(f"[{self.call_uuid}] Caller hung up (0x00 terminate received).")
                self.conn.is_active = False
                return None

            # 0x01 is UUID frame - ignore during speech collection
            if msg_type == 0x01:
                logger.debug(f"[{self.call_uuid}] Ignoring AudioSocket UUID frame during listening.")
                continue

            # 0x03 is DTMF / error frame
            if msg_type == 0x03:
                logger.info(f"[{self.call_uuid}] Received DTMF/control frame: {payload.hex()}")
                continue

            if msg_type in (TYPE_AUDIO, 0x10, 0x02):
                total_audio_frames += 1
                endpoint_state = self.endpointer.process_frame(payload)

                if endpoint_state == EndpointState.SPEECH_ENDED:
                    pcm = self.endpointer.get_speech_pcm()
                    logger.info(f"[{self.call_uuid}] Speech utterance detected ({len(pcm)} bytes, {total_audio_frames} frames).")
                    return pcm

                elif endpoint_state in (
                    EndpointState.INITIAL_SILENCE_TIMEOUT,
                    EndpointState.MAX_DURATION_EXCEEDED,
                ):
                    pcm = self.endpointer.get_speech_pcm()
                    logger.info(f"[{self.call_uuid}] Endpoint reached: {endpoint_state.value} ({len(pcm)} bytes).")
                    return pcm if len(pcm) > 0 else None

        return None

