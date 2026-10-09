"""Audio endpointing and Voice Activity Detection (VAD) for 8 kHz telephony streams.

Processes 20ms frames (160 samples / 320 bytes of 8 kHz 16-bit PCM).
Uses audio-time frame tracking (20ms per frame) for immune network jitter detection,
pre-roll pad for preserving onset consonants, and clean silence trimming.
"""
import audioop
import collections
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

    FRAME_MS = 20  # 320 bytes = 160 samples at 8kHz 16-bit PCM = 20ms

    def __init__(
        self,
        energy_threshold: int = 700,
        min_speech_ms: int = 200,
        silence_timeout_ms: int = 800,
        initial_silence_timeout_sec: float = 10.0,
        max_utterance_sec: float = 15.0,
    ):
        self.energy_threshold = energy_threshold
        self.min_speech_ms = min_speech_ms
        self.silence_timeout_ms = silence_timeout_ms
        self.initial_silence_timeout_sec = initial_silence_timeout_sec
        self.max_utterance_sec = max_utterance_sec
        self.last_rms = 0
        self.last_is_voiced = False

        # Pre-roll ring buffer (keep last 200ms = 10 frames before speech onset)
        self.pre_roll = collections.deque(maxlen=10)

        self.reset()

    def reset(self):
        """Reset state for a new listening turn."""
        self.state = EndpointState.WAITING_FOR_SPEECH
        self.speech_frames: list[bytes] = []
        self.pre_roll.clear()
        self.start_time: float = time.monotonic()
        self.voiced_ms: int = 0
        self.silence_ms: int = 0
        self.total_audio_ms: int = 0
        self.has_voiced = False
        self.last_rms = 0
        self.last_is_voiced = False

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
        self.last_rms = rms
        self.last_is_voiced = is_voiced
        self.total_audio_ms += self.FRAME_MS

        if self.state == EndpointState.WAITING_FOR_SPEECH:
            if is_voiced:
                self.state = EndpointState.SPEECH_IN_PROGRESS
                self.has_voiced = True
                self.voiced_ms = self.FRAME_MS
                self.silence_ms = 0
                # Prepend pre-roll frames so onset consonants (e.g. 'p', 't', 'k') are preserved
                self.speech_frames.extend(list(self.pre_roll))
                self.speech_frames.append(frame_bytes)
            else:
                self.pre_roll.append(frame_bytes)
                # Check initial silence timeout (both wall-clock and audio stream)
                if (now - self.start_time >= self.initial_silence_timeout_sec) or (
                    self.total_audio_ms >= int(self.initial_silence_timeout_sec * 1000)
                ):
                    self.state = EndpointState.INITIAL_SILENCE_TIMEOUT
                    return self.state

        elif self.state == EndpointState.SPEECH_IN_PROGRESS:
            self.speech_frames.append(frame_bytes)

            # Check max utterance limit (15s)
            if self.total_audio_ms >= int(self.max_utterance_sec * 1000):
                self.state = EndpointState.MAX_DURATION_EXCEEDED
                return self.state

            if is_voiced:
                self.voiced_ms += self.FRAME_MS
                self.silence_ms = 0
            else:
                self.silence_ms += self.FRAME_MS
                # If caller was speaking and is now silent for silence_timeout_ms (e.g. 800ms)
                if (
                    self.silence_ms >= self.silence_timeout_ms
                    and self.voiced_ms >= self.min_speech_ms
                ):
                    self.state = EndpointState.SPEECH_ENDED
                    return self.state

        return self.state

    def get_speech_pcm(self) -> bytes:
        """Return accumulated 8 kHz 16-bit PCM bytes for the utterance, trimming trailing silence."""
        # Trim trailing silence frames exceeding 200ms
        excess_silence_frames = max(0, (self.silence_ms - 200) // self.FRAME_MS)
        if excess_silence_frames > 0 and len(self.speech_frames) > excess_silence_frames:
            frames_to_return = self.speech_frames[:-excess_silence_frames]
        else:
            frames_to_return = self.speech_frames
        return b"".join(frames_to_return)

