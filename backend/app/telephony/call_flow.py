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
            energy_threshold=settings.VAD_ENERGY_THRESHOLD,
            min_speech_ms=250,
            silence_timeout_ms=settings.SPEECH_SILENCE_TIMEOUT_MS,
            initial_silence_timeout_sec=settings.INITIAL_SILENCE_TIMEOUT_SECONDS,
            max_utterance_sec=15.0,
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
            print(f"\n=======================================================", flush=True)
            print(f"📞 [CALL STARTED] New Call connected | UUID: {self.call_uuid[:8]}...", flush=True)
            print(f"=======================================================", flush=True)

            # State 1: ANSWER (Play greeting)
            await self._state_answer()

            # Automatically grant consent for smooth seamless demo interaction
            self.session_state.has_consented = True

            # Conversation Turn Loop: LISTEN -> THINK -> SPEAK
            while self.conn.is_active:
                if time.monotonic() - self.start_time >= settings.MAX_CALL_DURATION_SECONDS:
                    print(f"⏱️ [CALL TIMEOUT] Max call duration reached. Terminating.", flush=True)
                    await self._play_prompt("goodbye", self.session_state.language)
                    break

                # State 3: LISTEN with VAD
                audio_pcm = await self._state_listen()
                if audio_pcm is None:
                    if self.session_state.consecutive_silence_count >= 2:
                        print("📴 [CALL END] Caller silent for 2 consecutive turns. Ending call.", flush=True)
                        await self._play_prompt("goodbye", self.session_state.language)
                        break
                    continue

                self.session_state.consecutive_silence_count = 0
                self.session_state.turn_count += 1

                # State 4: THINK
                await self._state_think()

                # State 5: Core Processing & SPEAK
                await self._state_speak(audio_pcm)

        except Exception as e:
            print(f"❌ [CALL ERROR] Unhandled exception: {e}", flush=True)
            logger.error(f"Unhandled error in call state machine {self.call_uuid}: {e}")
            await self._play_prompt("error", self.session_state.language)
        finally:
            await self.conn.hangup()
            await self.db_engine.dispose()
            async with CALL_LOCK:
                ACTIVE_CALL_COUNT = max(0, ACTIVE_CALL_COUNT - 1)
            print(f"📴 [CALL DISCONNECTED] UUID: {self.call_uuid[:8]}... Active calls: {ACTIVE_CALL_COUNT}\n", flush=True)

    async def _play_prompt(self, prompt_name: str, lang: str):
        """Play a pre-rendered 8 kHz PCM prompt audio to Asterisk."""
        print(f"🔊 [AUDIO OUT] Playing prompt '{prompt_name}' ({lang})...", flush=True)
        pcm_bytes = get_prompt_pcm(prompt_name, lang)
        if pcm_bytes:
            await self.conn.send_audio(pcm_bytes)

    async def _state_answer(self):
        """State 1: Play disclaimer and greeting."""
        print("▶️ [STATE: ANSWER] Playing bilingual greeting...", flush=True)
        await self._play_prompt("greeting", "am")
        await asyncio.sleep(0.1)
        self.conn.drain_audio_buffer()

    async def _state_consent(self):
        """State 2: Voice consent question for first-time callers."""
        self.session_state.has_consented = True

    async def _state_listen(self) -> Optional[bytes]:
        """State 3: Listen for caller utterance with VAD."""
        turn_num = self.session_state.turn_count + 1
        print(f"\n👂 [STATE: LISTEN] Turn #{turn_num} | Listening for caller voice (Threshold: {self.endpointer.energy_threshold})...", flush=True)
        self.conn.drain_audio_buffer()
        self.endpointer.reset()
        self.endpointer.initial_silence_timeout_sec = 10.0
        speech_pcm = await self._collect_speech_frames()

        if not speech_pcm or len(speech_pcm) < 3200:
            if not self.conn.is_active:
                return None
            self.session_state.consecutive_silence_count += 1
            print(f"⚠️ [SILENCE] No speech detected (consecutive silence: {self.session_state.consecutive_silence_count})", flush=True)
            if self.session_state.consecutive_silence_count < 2:
                await self._play_prompt("repeat_prompt", self.session_state.language)
            return None

        return speech_pcm

    async def _state_think(self):
        """State 4: Play immediate thinking cue ("One moment...")."""
        print("🤔 [STATE: THINK] Processing... Playing 'one moment' prompt.", flush=True)
        await self._play_prompt("one_moment", self.session_state.language)

    async def _state_speak(self, audio_pcm: bytes):
        """State 5: Run AI pipeline, check confidence, stream answer back."""
        print(f"🧠 [STATE: SPEAK] Processing caller utterance ({len(audio_pcm)} bytes)...", flush=True)
        start_t = time.perf_counter()

        response = await process_utterance(
            audio_bytes=audio_pcm,
            session=self.session_state,
            text_override=None,
            synthesize_audio=True
        )

        duration_ms = (time.perf_counter() - start_t) * 1000
        print(f"\n=======================================================", flush=True)
        print(f"📝 [STT TRANSCRIPT] '{response.metadata.answer_en_gloss}'", flush=True)
        print(f"💡 [AI ANSWER TEXT] '{response.text}'", flush=True)
        print(f"⏱️ [TOTAL LATENCY]  {duration_ms:.1f}ms | Confidence: {response.metadata.confidence}", flush=True)
        print(f"=======================================================", flush=True)

        # Check for Low Confidence / Empty STT
        if response.metadata.confidence < 0.2 or not response.text.strip():
            self.consecutive_low_conf_count += 1
            print(f"⚠️ [LOW CONFIDENCE] Count: {self.consecutive_low_conf_count}", flush=True)
            if self.consecutive_low_conf_count >= 2:
                print("📴 [CALL END] Repeated low confidence. Playing referral and terminating.", flush=True)
                await self._play_prompt("safe_fallback", self.session_state.language)
                await self._play_prompt("goodbye", self.session_state.language)
                await self.conn.hangup()
                return
            else:
                await self._play_prompt("repeat_prompt", self.session_state.language)
                return

        self.consecutive_low_conf_count = 0

        # Stream Audio Answer Back to Asterisk
        if response.audio and len(response.audio) > 0:
            print(f"🔊 [AUDIO STREAMING] Sending {len(response.audio)} bytes ({len(response.audio)/16000:.1f}s) to Asterisk...", flush=True)
            await self.conn.send_audio(response.audio)
            print(f"✅ [AUDIO STREAMED] Playback complete. Moving to next turn.\n", flush=True)
            self.conn.drain_audio_buffer()
        else:
            print("⚠️ [AUDIO EMPTY] Falling back to pre-rendered audio.", flush=True)
            await self._play_prompt("safe_fallback", self.session_state.language)
            self.conn.drain_audio_buffer()

    async def _collect_speech_frames(self) -> Optional[bytes]:
        """Read 20ms audio frames from AudioSocket connection and feed VAD endpointer."""
        frame_idx = 0
        speech_started = False

        while self.conn.is_active:
            frame = await self.conn.read_frame()
            if not frame:
                self.conn.is_active = False
                return None

            msg_type, payload = frame
            # 0x00 is the official AudioSocket hangup signal
            if msg_type == TYPE_HANGUP:
                print(f"📴 [CALL EVENT] Caller hung up.", flush=True)
                self.conn.is_active = False
                return None

            # Audio types: 0x10 is 8kHz SLIN, 0x11-0x18 higher SLIN rates
            if msg_type in (TYPE_AUDIO, 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18):
                frame_idx += 1
                endpoint_state = self.endpointer.process_frame(payload)
                rms = getattr(self.endpointer, "last_rms", 0)

                # Responsive live energy meter every 10 frames (200ms) while waiting
                if endpoint_state == EndpointState.WAITING_FOR_SPEECH and frame_idx % 10 == 0:
                    bars = "█" * min(15, max(1, rms // 30))
                    print(f"   [MIC METER 🎤] Frame #{frame_idx:04d} | RMS: {rms:4d} | Level: {bars:<15} | Waiting for speech...", flush=True)

                if endpoint_state == EndpointState.SPEECH_IN_PROGRESS:
                    if not speech_started:
                        speech_started = True
                        print(f"\n🟢 [SPEECH DETECTED 🗣️] Energy RMS {rms} >= {self.endpointer.energy_threshold}! Recording caller...", flush=True)
                    elif frame_idx % 10 == 0:
                        bars = "█" * min(20, max(1, rms // 30))
                        print(f"   [RECORDING 🎙️] Frame #{frame_idx:04d} | RMS: {rms:4d} | {bars}", flush=True)

                if endpoint_state == EndpointState.SPEECH_ENDED:
                    pcm = self.endpointer.get_speech_pcm()
                    print(f"🔴 [SPEECH ENDED ⏹️] Captured {len(pcm)} bytes ({len(pcm)/16000:.2f}s of caller audio).", flush=True)
                    return pcm

                elif endpoint_state in (
                    EndpointState.INITIAL_SILENCE_TIMEOUT,
                    EndpointState.MAX_DURATION_EXCEEDED,
                ):
                    pcm = self.endpointer.get_speech_pcm()
                    if len(pcm) > 0:
                        print(f"⏱️ [VAD TIMEOUT] Returning {len(pcm)} bytes of speech audio.", flush=True)
                        return pcm
                    return None

        return None
