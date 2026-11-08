"""Call flow state machine and session orchestrator for Asterisk AudioSocket telephony.

Implements Location-Aware Agricultural AI Voice Call Flow:
- GREETING: Plays greeting and recording announcement without yes/no consent, followed immediately by location question.
- LOCATION_COLLECTION: Captures spoken location, cleans prefixes/suffixes, resolves to structured place.
- LOCATION_CLARIFICATION: If ambiguous, asks at most one concise clarification: "Which region is that in?".
- AGRICULTURAL_QUERY: Solicits agricultural crop/livestock symptoms in farmer's own words.
- KNOWLEDGE_RETRIEVAL: Retrieves evidence with geographic and agroecological boosts from pgvector & live search.
- RESPONSE_GENERATION: Grounded, practical advice in caller's language with Open-Meteo weather context.
- CLOSING: Clean exit and goodbye.
- COMPLETED: Finalize DB metrics, apply configured recording policy.
"""
import asyncio
import hashlib
import logging
import time
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

try:
    from app.config import settings
    from app.database.models import Call, ConversationMessage
    from app.pipeline import SessionState, is_goodbye_intent, process_utterance
    from app.stt import get_stt_provider
    from app.telephony.audiosocket_server import (
        TYPE_AUDIO,
        TYPE_HANGUP,
        AudioSocketConnection,
    )
    from app.telephony.endpointing import EndpointState, VADEndpointer
    from app.telephony.live_logger import log_telephony_event
    from app.telephony.prompts_audio import get_prompt_pcm
    from app.weather.location import (
        LocationMatch,
        resolve_location,
    )
except ImportError:
    from backend.app.config import settings
    from backend.app.database.models import Call, ConversationMessage
    from backend.app.pipeline import SessionState, is_goodbye_intent, process_utterance
    from backend.app.stt import get_stt_provider
    from backend.app.telephony.audiosocket_server import (
        TYPE_AUDIO,
        TYPE_HANGUP,
        AudioSocketConnection,
    )
    from backend.app.telephony.endpointing import EndpointState, VADEndpointer
    from backend.app.telephony.live_logger import log_telephony_event
    from backend.app.telephony.prompts_audio import get_prompt_pcm
    from backend.app.weather.location import (
        LocationMatch,
        resolve_location,
    )

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

        self.current_state = "GREETING"
        self.session_state = SessionState(
            session_id=self.call_uuid,
            caller_hash=self.caller_hash,
            language="am",
            is_first_time=True,
            has_consented=True,
            turn_count=0,
            consecutive_silence_count=0,
            call_stage="GREETING",
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

    async def _init_call_record(self):
        """Create initial Call record in PostgreSQL with recording consent notice status."""
        try:
            async with self.session_factory() as db:
                call_rec = Call(
                    id=self.call_uuid,
                    caller_hash=self.caller_hash,
                    language=self.session_state.language,
                    is_first_time=self.session_state.is_first_time,
                    reached_answer=False,
                    started_at=datetime.utcnow(),
                    end_reason="in_progress",
                    recording_consent_status="notice_announced",
                )
                db.add(call_rec)
                await db.commit()
                logger.info(f"Initialized call record {self.call_uuid} in PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to initialize call record in DB: {e}")

    async def _update_call_location(self):
        """Update Call record with resolved location and agroecological metadata."""
        try:
            async with self.session_factory() as db:
                stmt = select(Call).where(Call.id == self.call_uuid)
                res = await db.execute(stmt)
                call_rec = res.scalar_one_or_none()
                if call_rec:
                    call_rec.location_name = self.session_state.location_name
                    call_rec.region = self.session_state.location_region
                    call_rec.zone = self.session_state.location_zone
                    call_rec.woreda = self.session_state.location_woreda
                    call_rec.location_confidence = self.session_state.location_confidence
                    call_rec.agroecological_zone = self.session_state.agroecological_zone
                    await db.commit()
                    logger.info(
                        f"Updated Call record {self.call_uuid} with location: "
                        f"{self.session_state.location_name} ({self.session_state.location_region})"
                    )
        except Exception as e:
            logger.error(f"Failed to update location on call record: {e}")

    async def _save_turn_messages(self, caller_text: str, assistant_text: str, grounded: bool):
        """Save caller and assistant messages to conversation_messages table and session history."""
        try:
            if caller_text:
                self.session_state.history.append({"role": "user", "text": caller_text})
            if assistant_text:
                self.session_state.history.append({"role": "assistant", "text": assistant_text})

            async with self.session_factory() as db:
                if caller_text:
                    db.add(ConversationMessage(
                        call_id=self.call_uuid,
                        speaker="caller",
                        text=caller_text,
                        created_at=datetime.utcnow(),
                    ))
                if assistant_text:
                    db.add(ConversationMessage(
                        call_id=self.call_uuid,
                        speaker="assistant",
                        text=assistant_text,
                        created_at=datetime.utcnow(),
                    ))
                stmt = select(Call).where(Call.id == self.call_uuid)
                res = await db.execute(stmt)
                call_rec = res.scalar_one_or_none()
                if call_rec:
                    if grounded:
                        call_rec.reached_answer = True
                    call_rec.language = self.session_state.language
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to save turn messages to DB: {e}")

    async def _finalize_call_record(self, end_reason: str):
        """Finalize call duration, end reason, and timestamps in PostgreSQL, and queue post-call SMS."""
        try:
            duration = int(time.monotonic() - self.start_time)
            reached_ans = False
            async with self.session_factory() as db:
                stmt = select(Call).where(Call.id == self.call_uuid)
                res = await db.execute(stmt)
                call_rec = res.scalar_one_or_none()
                if call_rec:
                    call_rec.ended_at = datetime.utcnow()
                    call_rec.duration_seconds = max(1, duration)
                    call_rec.end_reason = end_reason
                    reached_ans = call_rec.reached_answer
                    await db.commit()
                else:
                    reached_ans = (self.session_state.turn_count > 0)
                    call_rec = Call(
                        id=self.call_uuid,
                        caller_hash=self.caller_hash,
                        language=self.session_state.language,
                        duration_seconds=max(1, duration),
                        started_at=datetime.utcnow(),
                        ended_at=datetime.utcnow(),
                        end_reason=end_reason,
                        reached_answer=reached_ans,
                        recording_consent_status="notice_announced",
                    )
                    db.add(call_rec)
                    await db.commit()
                logger.info(f"Finalized call {self.call_uuid} in DB: duration={duration}s, reason={end_reason}")

            # Trigger post-call SMS summary if call had conversational turns
            if self.session_state.turn_count > 0:
                try:
                    try:
                        from app.sms.dispatcher import trigger_post_call_summary
                    except ImportError:
                        from backend.app.sms.dispatcher import trigger_post_call_summary

                    last_advice = None
                    for msg in reversed(self.session_state.history):
                        if msg.get("role") == "assistant" and msg.get("text") and "Which area" not in msg.get("text"):
                            last_advice = msg.get("text")
                            break

                    if not last_advice:
                        async with self.session_factory() as db:
                            stmt = (
                                select(ConversationMessage)
                                .where(
                                    ConversationMessage.call_id == self.call_uuid,
                                    ConversationMessage.speaker == "assistant",
                                )
                                .order_by(desc(ConversationMessage.created_at))
                            )
                            res = await db.execute(stmt)
                            msgs = res.scalars().all()
                            for m in msgs:
                                if m.text and "Which area" not in m.text:
                                    last_advice = m.text
                                    break

                    await trigger_post_call_summary(
                        call_id=self.call_uuid,
                        caller_hash=self.caller_hash,
                        language=self.session_state.language,
                        last_advice=last_advice,
                        reached_answer=reached_ans or bool(last_advice),
                        crop=self.session_state.extracted_crop,
                    )
                except Exception as sms_err:
                    logger.warning(f"Could not trigger post-call SMS: {sms_err}")

        except Exception as e:
            logger.error(f"Failed to finalize call record in DB: {e}")

    async def run(self):
        """Main entry point running the explicit 3-step opening and conversation state machine."""
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

        end_reason = "completed"
        try:
            print("\n=======================================================", flush=True)
            print(f"📞 [CALL STARTED] New Call connected | UUID: {self.call_uuid[:8]}...", flush=True)
            print("=======================================================", flush=True)
            log_telephony_event("INFO", "[CALL STARTED]", f"Incoming caller connected from Asterisk PBX", call_id=self.call_uuid)

            # Persist initial call record to database
            await self._init_call_record()

            # Step 1: GREETING & RECORDING ANNOUNCEMENT
            self.current_state = "GREETING"
            self.session_state.call_stage = "GREETING"
            await self._state_greeting()

            if not self.conn.is_active:
                end_reason = "caller_hangup"
                return

            # Step 2: LOCATION_COLLECTION
            self.current_state = "LOCATION_COLLECTION"
            self.session_state.call_stage = "LOCATION_COLLECTION"
            loc_result, ambig_info = await self._state_collect_location()

            if not self.conn.is_active:
                end_reason = "caller_hangup"
                return

            if loc_result == "TERMINATE":
                end_reason = "max_silence"
                return

            # Step 2b: LOCATION_CLARIFICATION (only if ambiguous)
            if loc_result == "AMBIGUOUS" and ambig_info is not None:
                self.current_state = "LOCATION_CLARIFICATION"
                self.session_state.call_stage = "LOCATION_CLARIFICATION"
                await self._state_clarify_location(ambig_info)
                if not self.conn.is_active:
                    end_reason = "caller_hangup"
                    return

            # Check if caller already asked their farming problem during location collection
            if loc_result == "PROBLEM_ALREADY_SPOKEN" and ambig_info is not None:
                print("🌾 [DIRECT QUERY] Answering farming problem spoken during location prompt...", flush=True)
                self.current_state = "RESPONSE_GENERATION"
                self.session_state.call_stage = "RESPONSE_GENERATION"
                self.session_state.consecutive_silence_count = 0
                self.session_state.turn_count += 1
                is_completed = await self._state_speak(ambig_info)
                if is_completed:
                    self.current_state = "CLOSING"
            else:
                # Step 3: AGRICULTURAL_QUERY Transition
                self.current_state = "AGRICULTURAL_QUERY"
                self.session_state.call_stage = "AGRICULTURAL_QUERY"
                await self._play_prompt("ask_problem", self.session_state.language)
                await asyncio.sleep(0.15)
                await self.conn.drain_audio_buffer()

            # Main Agricultural Conversation Turn Loop: LISTEN -> RETRIEVE -> SPEAK
            while self.conn.is_active and self.current_state != "CLOSING":
                if time.monotonic() - self.start_time >= settings.MAX_CALL_DURATION_SECONDS:
                    print("⏱️ [CALL TIMEOUT] Max call duration reached. Terminating.", flush=True)
                    end_reason = "timeout"
                    self.current_state = "CLOSING"
                    await self._play_prompt("goodbye", self.session_state.language)
                    break

                # State: LISTEN for farming problem or follow-up
                audio_pcm = await self._state_listen()
                if audio_pcm is None:
                    max_reminders = getattr(settings, "MAX_SILENCE_REMINDERS", 2)
                    if self.session_state.consecutive_silence_count >= max_reminders:
                        print(f"📴 [CALL END] Caller silent for {max_reminders} consecutive reminders. Ending call.", flush=True)
                        end_reason = "max_silence"
                        self.current_state = "CLOSING"
                        await self._play_prompt("goodbye", self.session_state.language)
                        break
                    continue

                self.session_state.consecutive_silence_count = 0
                self.session_state.turn_count += 1

                is_completed = await self._state_speak(audio_pcm)

                if is_completed:
                    self.current_state = "CLOSING"
                    print("📴 [CALL CLOSING] Closing phrase delivered. Waiting 3 seconds before ending call...", flush=True)
                    log_telephony_event("INFO", "[CALL CLOSING]", "Closing phrase delivered. Waiting 3 seconds before ending call.", call_id=self.call_uuid)
                    await asyncio.sleep(3.0)
                    break

            self.current_state = "COMPLETED"

        except Exception as e:
            end_reason = "error"
            print(f"❌ [CALL ERROR] Unhandled exception: {e}", flush=True)
            log_telephony_event("ERROR", "[CALL ERROR]", f"Exception in call state machine: {e}", call_id=self.call_uuid)
            logger.error(f"Unhandled error in call state machine {self.call_uuid}: {e}")
            await self._play_prompt("error", self.session_state.language)
        finally:
            await self._finalize_call_record(end_reason)
            await self.conn.hangup()
            await self.db_engine.dispose()
            async with CALL_LOCK:
                ACTIVE_CALL_COUNT = max(0, ACTIVE_CALL_COUNT - 1)
            print(f"📴 [CALL DISCONNECTED] UUID: {self.call_uuid[:8]}... Active calls: {ACTIVE_CALL_COUNT}\n", flush=True)
            log_telephony_event("INFO", "[CALL DISCONNECTED]", f"Call closed. Duration: {int(time.monotonic() - self.start_time)}s, reason: {end_reason}", call_id=self.call_uuid)

    async def _play_prompt(self, prompt_name: str, lang: str):
        """Play a pre-rendered 8 kHz PCM prompt audio to Asterisk."""
        print(f"🔊 [AUDIO OUT] Playing prompt '{prompt_name}' ({lang})...", flush=True)
        log_telephony_event("AUDIO", "[AUDIO PROMPT]", f"Playing prompt '{prompt_name}' ({lang})", call_id=self.call_uuid)
        pcm_bytes = get_prompt_pcm(prompt_name, lang)
        if pcm_bytes:
            await self.conn.send_audio(pcm_bytes)

    async def _state_greeting(self):
        """Step 1: GREETING & RECORDING ANNOUNCEMENT.

        Plays the prompt greeting that announces recording for service improvement:
        "Hello, welcome to Hello Farmer. This call is being recorded to improve our service."
        """
        print("▶️ [STATE: GREETING] Playing greeting announcement & recording disclosure...", flush=True)
        await self._play_prompt("greeting", self.session_state.language)
        await asyncio.sleep(0.15)
        await self.conn.drain_audio_buffer()

    async def _state_collect_location(self) -> Tuple[str, Optional[Tuple[LocationMatch, str]]]:
        """Step 2: LOCATION_COLLECTION.

        Asks for caller's area/town/city, transcribes, and resolves to structured geography.
        Returns:
            Tuple of (status, ambiguous_info). If ambiguous_info is not None, clarification is required.
        """
        print("▶️ [STATE: LOCATION_COLLECTION] Asking for caller's area...", flush=True)
        await self._play_prompt("ask_location", self.session_state.language)
        await asyncio.sleep(0.15)
        await self.conn.drain_audio_buffer()

        silence_count = 0
        max_reminders = getattr(settings, "MAX_SILENCE_REMINDERS", 2)
        spoken_text = ""
        audio_pcm = None

        while silence_count <= max_reminders and self.conn.is_active:
            self.endpointer.energy_threshold = int(getattr(settings, "VAD_ENERGY_THRESHOLD", 450))
            self.endpointer.silence_timeout_ms = 350
            self.endpointer.min_speech_ms = 180
            self.endpointer.max_utterance_sec = 3.5
            self.endpointer.reset()
            self.endpointer.initial_silence_timeout_sec = float(getattr(settings, "INITIAL_SILENCE_TIMEOUT_SECONDS", 10))
            audio_pcm = await self._collect_speech_frames()

            if not self.conn.is_active:
                return ("TERMINATE", None)

            if audio_pcm and len(audio_pcm) >= 3200:
                # Transcribe captured speech with keepalive so Asterisk socket stays alive
                self.conn.start_keepalive()
                try:
                    stt = get_stt_provider()
                    transcript = await stt.transcribe(audio_pcm, language=self.session_state.language, context="location")
                finally:
                    self.conn.stop_keepalive()
                spoken_text = transcript.text.strip()
                print(f"📝 [LOCATION TRANSCRIPT] Spoken location: '{spoken_text}' (conf: {transcript.confidence})", flush=True)
                log_telephony_event("SPEECH", "[LOCATION STT]", f"Location speech recognized: '{spoken_text}'", call_id=self.call_uuid, details={"transcript": spoken_text, "confidence": transcript.confidence})

                if spoken_text and len(spoken_text) >= 2:
                    break

            silence_count += 1
            if silence_count <= max_reminders:
                print(f"⚠️ [SILENCE/NOISE] Location speech empty or brief noise (reminder #{silence_count}/{max_reminders}). Prompting gently...", flush=True)
                await self._play_prompt("ask_location", self.session_state.language)
                await asyncio.sleep(0.15)
                await self.conn.drain_audio_buffer()
            else:
                print("⚠️ [LOCATION UNKNOWN] Max silence/unintelligible reached. Proceeding with general guidance.", flush=True)
                break

        if not self.conn.is_active:
            return ("TERMINATE", None)

        if not spoken_text:
            print("⚠️ [EMPTY STT] Proceeding with general guidance (location unknown).", flush=True)
            return ("SUCCESS", None)

        # Save caller utterance to DB in background task so audio is not blocked
        asyncio.create_task(
            self._save_turn_messages(
                caller_text=spoken_text,
                assistant_text="Which area are you calling from?",
                grounded=False,
            )
        )

        # Check for goodbye/hangup intent early
        if is_goodbye_intent(spoken_text, self.session_state.language):
            await self._play_prompt("goodbye", self.session_state.language)
            await asyncio.sleep(3.0)
            return ("TERMINATE", None)

        # Resolve location
        loc = resolve_location(spoken_text)
        if loc:
            log_telephony_event("AI", "[LOCATION MATCH]", f"Resolved location to {loc.woreda}, {loc.region} ({loc.agroecological_zone})", call_id=self.call_uuid)

        if loc:
            if loc.is_ambiguous:
                print(f"⚠️ [LOCATION AMBIGUOUS] '{loc.name}' is ambiguous across regions: {loc.ambiguous_regions}", flush=True)
                return ("AMBIGUOUS", (loc, spoken_text))

            # Fully resolved
            self._apply_resolved_location(loc)
            asyncio.create_task(self._update_call_location())
            print(
                f"✅ [LOCATION RESOLVED] {loc.name} | Region: {loc.region} | "
                f"Zone: {loc.zone} | Agroecology: {loc.agroecological_zone} (conf: {loc.confidence})",
                flush=True,
            )
        else:
            # Critical requirement: Never silently default an unknown location to Addis Ababa or any other place!
            print("⚠️ [LOCATION UNKNOWN] Unrecognized location. Proceeding with general guidance (NO silent default).", flush=True)
            self.session_state.location_name = None
            self.session_state.location_region = None
            self.session_state.location_zone = None
            self.session_state.location_woreda = None
            self.session_state.location_latitude = None
            self.session_state.location_longitude = None
            self.session_state.location_confidence = 0.0

            # Check if caller already asked their farming problem (e.g. 'ጤፍ ላይ ቢጫ ቅጠል ታይቷል')
            try:
                try:
                    from app.farmer_context.extraction import extract_context_from_utterance
                except ImportError:
                    from backend.app.farmer_context.extraction import extract_context_from_utterance
                extracted = extract_context_from_utterance(spoken_text, language=self.session_state.language)
                agri_keywords = ["ቅጠል", "ተባይ", "ማዳበሪያ", "ውሃ", "በሽታ", "ምርት", "ዘር", "ጤፍ", "ስንዴ", "በቆሎ", "problem", "crop", "leaf", "disease", "fertilizer", "yellow", "pest"]
                has_agri_intent = bool(extracted.crop or extracted.symptoms or any(kw in spoken_text for kw in agri_keywords))
                if has_agri_intent:
                    print(f"🌾 [EARLY QUESTION DETECTED] Caller already stated farming problem: '{spoken_text}'", flush=True)
                    return ("PROBLEM_ALREADY_SPOKEN", audio_pcm)
            except Exception as e:
                logger.debug("Early context extraction check: %s", e)

        return ("SUCCESS", None)

    async def _state_clarify_location(self, ambig_info: Tuple[LocationMatch, str]):
        """Step 2b: LOCATION_CLARIFICATION.

        Asks at most one concise clarification: "Which region is that in?" / "በየትኛው ክልል ውስጥ ነው?".
        """
        ambig_loc, orig_spoken = ambig_info
        print("▶️ [STATE: LOCATION_CLARIFICATION] Asking region clarification...", flush=True)
        await self._play_prompt("clarify_region", self.session_state.language)
        await asyncio.sleep(0.15)
        await self.conn.drain_audio_buffer()

        self.endpointer.reset()
        self.endpointer.initial_silence_timeout_sec = float(getattr(settings, "INITIAL_SILENCE_TIMEOUT_SECONDS", 8))
        audio_pcm = await self._collect_speech_frames()

        if audio_pcm and len(audio_pcm) >= 3200:
            self.conn.start_keepalive()
            try:
                stt = get_stt_provider()
                transcript = await stt.transcribe(audio_pcm, language=self.session_state.language)
            finally:
                self.conn.stop_keepalive()
            region_answer = transcript.text.strip()
            print(f"📝 [REGION CLARIFICATION] Caller replied: '{region_answer}'", flush=True)

            await self._save_turn_messages(
                caller_text=region_answer,
                assistant_text="Which region is that in?",
                grounded=False,
            )

            # Re-resolve with region hint
            loc_resolved = resolve_location(orig_spoken, region_hint=region_answer)
            if not loc_resolved:
                loc_resolved = resolve_location(region_answer)

            if loc_resolved:
                self._apply_resolved_location(loc_resolved)
                await self._update_call_location()
                print(
                    f"✅ [LOCATION CLARIFIED] {loc_resolved.name} | Region: {loc_resolved.region} | "
                    f"Agroecology: {loc_resolved.agroecological_zone}",
                    flush=True,
                )
            else:
                print("⚠️ [CLARIFICATION UNRESOLVED] Region clarification did not match. Continuing with general guidance.", flush=True)
        else:
            print("⚠️ [CLARIFICATION SILENCE] No answer to region clarification. Continuing with original best match or general guidance.", flush=True)
            if ambig_loc:
                self._apply_resolved_location(ambig_loc)
                await self._update_call_location()

    def _apply_resolved_location(self, loc: LocationMatch):
        """Set session state fields from resolved LocationMatch."""
        self.session_state.location_name = loc.name
        self.session_state.location_region = loc.region
        self.session_state.location_zone = loc.zone
        self.session_state.location_woreda = loc.woreda
        self.session_state.location_latitude = loc.latitude
        self.session_state.location_longitude = loc.longitude
        self.session_state.location_confidence = loc.confidence
        self.session_state.agroecological_zone = loc.agroecological_zone

    async def _state_listen(self) -> Optional[bytes]:
        """State: Listen for caller utterance with VAD."""
        self.endpointer.energy_threshold = int(getattr(settings, "VAD_ENERGY_THRESHOLD", 450))
        self.endpointer.silence_timeout_ms = 900
        self.endpointer.max_utterance_sec = 8.0
        turn_num = self.session_state.turn_count + 1
        print(f"\n👂 [STATE: LISTEN] Turn #{turn_num} | Listening for caller voice (Threshold: {self.endpointer.energy_threshold})...", flush=True)
        log_telephony_event("SPEECH", "[LISTENING]", f"Turn #{turn_num}: Listening for caller voice (VAD threshold: {self.endpointer.energy_threshold})", call_id=self.call_uuid)
        await self.conn.drain_audio_buffer()
        self.endpointer.reset()
        self.endpointer.initial_silence_timeout_sec = float(getattr(settings, "INITIAL_SILENCE_TIMEOUT_SECONDS", 12))
        speech_pcm = await self._collect_speech_frames()

        if not speech_pcm or len(speech_pcm) < 3200:
            if not self.conn.is_active:
                return None
            self.session_state.consecutive_silence_count += 1
            max_reminders = getattr(settings, "MAX_SILENCE_REMINDERS", 2)
            print(f"⚠️ [SILENCE] No speech detected (consecutive silence: {self.session_state.consecutive_silence_count}/{max_reminders})", flush=True)
            if self.session_state.consecutive_silence_count < max_reminders:
                # Play natural listening reminder cue ("እየሰማሁዎት ነው፣ እባክዎ ጥያቄዎን ይናገሩ")
                await self._play_prompt("listening_reminder", self.session_state.language)
            return None

        return speech_pcm

    async def _state_speak(self, audio_pcm: bytes) -> bool:
        """States: KNOWLEDGE_RETRIEVAL & RESPONSE_GENERATION & SPEAK.

        Runs location-aware RAG retrieval, invokes LLM with weather and agroecological context,
        synthesizes answer, and streams chunked audio back to Asterisk.
        Supports full-duplex barge-in interruption.
        Returns True if call should end (e.g. goodbye).
        """
        print(f"🧠 [STATE: RETRIEVAL & GENERATION] Processing agricultural query ({len(audio_pcm)} bytes)...", flush=True)
        log_telephony_event("AI", "[RAG RETRIEVAL]", f"Running agricultural knowledge retrieval ({len(audio_pcm)} bytes)...", call_id=self.call_uuid)

        start_t = time.perf_counter()

        # Launch pipeline processing task concurrently in background
        proc_task = asyncio.create_task(
            process_utterance(
                audio_bytes=audio_pcm,
                session=self.session_state,
                text_override=None,
                synthesize_audio=True,
            )
        )

        # 1. Immediately acknowledge caller query so they know the system is actively searching
        await self._play_prompt("one_moment", self.session_state.language)

        # Start continuous keepalive immediately so Asterisk AudioSocket channel NEVER experiences a frame gap
        self.conn.start_keepalive()

        # 2. Progressive Holding Cue: If processing takes longer than the first cue, play reassurance prompt
        # so there is never dead air or silence on the line
        if not proc_task.done():
            done, _ = await asyncio.wait([proc_task], timeout=1.8)
            if not done and self.conn.is_active:
                self.conn.stop_keepalive()
                print("🔄 [PROGRESSIVE HOLDING CUE] AI reasoning in progress... Playing reassurance holding prompt.", flush=True)
                await self._play_prompt("still_checking", self.session_state.language)
                self.conn.start_keepalive()

        try:
            response = await proc_task
        finally:
            self.conn.stop_keepalive()

        duration_ms = (time.perf_counter() - start_t) * 1000
        print("\n=======================================================", flush=True)
        print(f"📝 [USER TRANSCRIPT] '{getattr(response.metadata, 'user_transcript', None)}'", flush=True)
        print(f"💡 [AI ANSWER TEXT]  '{response.text}'", flush=True)
        print(f"⏱️ [TOTAL LATENCY]   {duration_ms:.1f}ms | Confidence: {response.metadata.confidence}", flush=True)
        if response.metadata.sources_used:
            print(f"📚 [SOURCES USED]    {len(response.metadata.sources_used)} source(s)", flush=True)
            for s in response.metadata.sources_used[:3]:
                print(f"   - {s.get('title')} (score: {s.get('score', 0):.2f})", flush=True)
        print("=======================================================", flush=True)

        # Save turn transcript to database
        caller_txt = (
            getattr(response.metadata, "user_transcript", None)
            or getattr(response.metadata, "answer_en_gloss", None)
            or "Caller utterance"
        )
        log_telephony_event("AI", "[USER QUESTION]", f"Caller: '{caller_txt}'", call_id=self.call_uuid, details={"transcript": caller_txt})
        log_telephony_event("AI", "[AI ANSWER]", f"Assistant: '{response.text[:100]}...' (Confidence: {response.metadata.confidence:.2f}, Latency: {duration_ms:.0f}ms)", call_id=self.call_uuid, details={"answer": response.text})
        # Save turn messages to DB in background task so TTS audio playback starts immediately
        asyncio.create_task(
            self._save_turn_messages(
                caller_text=caller_txt,
                assistant_text=response.text,
                grounded=getattr(response.metadata, "grounded", True),
            )
        )

        # Check for goodbye
        if getattr(response.metadata, "topic", None) == "goodbye":
            if response.audio and len(response.audio) > 0:
                print(f"🔊 [GOODBYE AUDIO] Streaming closing phrase to caller ({len(response.audio)} bytes)...", flush=True)
                await self.conn.send_audio(response.audio, pace=True)
            else:
                await self._play_prompt("goodbye", self.session_state.language)
            return True

        # Check for Low Confidence / Empty STT
        if response.metadata.confidence < 0.2 or not response.text.strip():
            self.consecutive_low_conf_count += 1
            print(f"⚠️ [LOW CONFIDENCE] Count: {self.consecutive_low_conf_count}", flush=True)
            if self.consecutive_low_conf_count >= 2:
                print("📴 [CALL END] Repeated low confidence. Playing referral and terminating.", flush=True)
                await self._play_prompt("safe_fallback", self.session_state.language)
                await self._play_prompt("goodbye", self.session_state.language)
                await self.conn.hangup()
                return True
            else:
                await self._play_prompt("repeat_prompt", self.session_state.language)
                return False

        self.consecutive_low_conf_count = 0

        # Stream Audio Answer Back to Asterisk with Full-Duplex Barge-In
        if response.audio and len(response.audio) > 0:
            barge_in_allowed = getattr(settings, "BARGE_IN_ENABLED", False)
            print(f"🔊 [AUDIO STREAMING] Sending {len(response.audio)} bytes ({len(response.audio)/16000:.1f}s) to Asterisk (barge-in={barge_in_allowed})...", flush=True)
            completed = await self.conn.send_audio(
                response.audio,
                pace=True,
                allow_barge_in=barge_in_allowed,
                barge_in_threshold=getattr(settings, "BARGE_IN_ENERGY_THRESHOLD", 550),
            )
            if not completed and barge_in_allowed:
                print("⚡ [BARGE-IN] Caller interrupted agent answer. Transitioning directly to listening...", flush=True)
                return False
            print("✅ [AUDIO STREAMED] Playback complete.\n", flush=True)
            await asyncio.sleep(0.15)
            await self.conn.drain_audio_buffer()
            # If the response already ended with an interactive conversational question,
            # transition directly to listening so the dialogue flows naturally.
            ans_text = (response.text or "").strip()
            ends_with_question = ans_text.endswith("?") or ans_text.endswith("፧") or bool(getattr(response.metadata, "follow_up_question", None))
            if getattr(response.metadata, "topic", None) != "goodbye" and not ends_with_question:
                await self._play_prompt("anything_else", self.session_state.language)
                await asyncio.sleep(0.15)
                await self.conn.drain_audio_buffer()
        else:
            print("⚠️ [AUDIO EMPTY] Falling back to pre-rendered audio.", flush=True)
            await self._play_prompt("safe_fallback", self.session_state.language)
            await asyncio.sleep(0.15)
            await self.conn.drain_audio_buffer()

        return False

    async def _collect_speech_frames(self) -> Optional[bytes]:
        """Read 20ms audio frames from AudioSocket connection and feed VAD endpointer."""
        frame_idx = 0
        speech_started = False

        # If barge-in occurred, pre-feed speech onset frames to endpointer
        if hasattr(self.conn, "barge_in_buffer") and self.conn.barge_in_buffer:
            print(f"🎙️ [BARGE-IN ONSET] Feeding {len(self.conn.barge_in_buffer)} preserved frames to VAD...", flush=True)
            for onset_frame in self.conn.barge_in_buffer:
                frame_idx += 1
                endpoint_state = self.endpointer.process_frame(onset_frame)
                if endpoint_state == EndpointState.SPEECH_IN_PROGRESS and not speech_started:
                    speech_started = True
            self.conn.barge_in_buffer = []

        while self.conn.is_active:
            frame = await self.conn.read_frame()
            if not frame:
                self.conn.is_active = False
                return None

            msg_type, payload = frame
            # 0x00 is the official AudioSocket hangup signal
            if msg_type == TYPE_HANGUP:
                print("📴 [CALL EVENT] Caller hung up.", flush=True)
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
                        log_telephony_event("SPEECH", "[SPEECH DETECTED]", f"Caller speaking! RMS: {rms} >= {self.endpointer.energy_threshold}", call_id=self.call_uuid, details={"rms": rms})
                    elif frame_idx % 10 == 0:
                        bars = "█" * min(20, max(1, rms // 30))
                        print(f"   [RECORDING 🎙️] Frame #{frame_idx:04d} | RMS: {rms:4d} | {bars}", flush=True)

                if endpoint_state == EndpointState.SPEECH_ENDED:
                    pcm = self.endpointer.get_speech_pcm()
                    print(f"🔴 [SPEECH ENDED ⏹️] Captured {len(pcm)} bytes ({len(pcm)/16000:.2f}s of caller audio).", flush=True)
                    log_telephony_event("SPEECH", "[SPEECH CAPTURED]", f"Captured {len(pcm)} bytes ({len(pcm)/16000:.2f}s) of caller audio", call_id=self.call_uuid)
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


