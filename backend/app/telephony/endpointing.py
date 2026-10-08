"""Audio endpointing and Voice Activity Detection (VAD) for 8 kHz telephony streams.

Processes 20ms frames (160 samples / 320 bytes of 8 kHz 16-bit PCM).
Detects start of speech, tracks continuous voice activity, and triggers
speech-ended when post-speech silence exceeds configurable threshold (e.g. 1000ms).
"""
import audioop
import enum
import time
from typing import Optional


class EndpointState(enum.Enum):
    WAITING_FOR_SPEECH = "waiting_for_speech"
    SPEECH_IN_PROGRESS = "speech_in_progress"
    SPEECH_ENDED = "speech_ended"
    INITIAL_SILENCE_TIMEOUT = "initial_silence_timeout"
    MAX_DURATION_EXCEEDED = "max_duration_exceeded"


class VADEndpointer:
    """Accumulates incoming 8 kHz 16-bit mono PCM frames and detects utterance boundaries."""

    def __init__(
        self,
        energy_threshold: int = 400,
        min_speech_ms: int = 250,
        silence_timeout_ms: int = 1000,
        initial_silence_timeout_sec: float = 10.0,
        max_utterance_sec: float = 30.0,
    ):
        self.energy_threshold = energy_threshold
        self.min_speech_ms = min_speech_ms
        self.silence_timeout_ms = silence_timeout_ms
        self.initial_silence_timeout_sec = initial_silence_timeout_sec
        self.max_utterance_sec = max_utterance_sec

        self.reset()

    def reset(self):
        """Reset state for a new listening turn."""
        self.state = EndpointState.WAITING_FOR_SPEECH
        self.speech_frames: list[bytes] = []
        self.start_time: float = time.monotonic()
        self.speech_start_time: Optional[float] = None
        self.silence_start_time: Optional[float] = None
        self.has_voiced = False

    def process_frame(self, frame_bytes: bytes, current_time: Optional[float] = None) -> EndpointState:
        """Process a 20ms (320 bytes) 8 kHz 16-bit PCM frame.

        Returns updated EndpointState.
        """
        now = current_time if current_time is not None else time.monotonic()
        if len(frame_bytes) < 4:
            return self.state

        # Compute RMS energy of 16-bit mono PCM
        rms = audioop.rms(frame_bytes, 2)
        is_voiced = rms >= self.energy_threshold

        if self.state == EndpointState.WAITING_FOR_SPEECH:
            if is_voiced:
                self.state = EndpointState.SPEECH_IN_PROGRESS
                self.speech_start_time = now
                self.speech_frames.append(frame_bytes)
                self.silence_start_time = None
                self.has_voiced = True
            else:
                # Check initial silence timeout
                if now - self.start_time >= self.initial_silence_timeout_sec:
                    self.state = EndpointState.INITIAL_SILENCE_TIMEOUT
                    return self.state

        elif self.state == EndpointState.SPEECH_IN_PROGRESS:
            self.speech_frames.append(frame_bytes)

            # Check max utterance limit
            if now - self.start_time >= self.max_utterance_sec:
                self.state = EndpointState.MAX_DURATION_EXCEEDED
                return self.state

            if is_voiced:
                self.silence_start_time = None
            else:
                if self.silence_start_time is None:
                    self.silence_start_time = now
                else:
                    silence_duration_ms = (now - self.silence_start_time) * 1000
                    start_t = self.speech_start_time if self.speech_start_time is not None else now
                    speech_duration_ms = (now - start_t) * 1000
                    if (
                        silence_duration_ms >= self.silence_timeout_ms
                        and speech_duration_ms >= self.min_speech_ms
                    ):
                        self.state = EndpointState.SPEECH_ENDED
                        return self.state

        return self.state

    def get_speech_pcm(self) -> bytes:
        """Return all accumulated 8 kHz 16-bit PCM bytes for the utterance."""
        return b"".join(self.speech_frames)
