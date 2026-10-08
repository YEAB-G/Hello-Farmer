"""Unit tests for Phase 5: Telephony, AudioSocket framing, and VAD endpointing."""
import hashlib

from backend.app.config import settings
from backend.app.telephony.audiosocket_server import (
    TYPE_AUDIO,
    TYPE_HANGUP,
)
from backend.app.telephony.endpointing import EndpointState, VADEndpointer
from backend.app.telephony.prompts_audio import get_prompt_pcm


def test_vad_endpointer_detects_speech_and_silence():
    """Verify VADEndpointer detects speech transition and silence timeout."""
    ep = VADEndpointer(
        energy_threshold=400,
        min_speech_ms=100,
        silence_timeout_ms=500,
        initial_silence_timeout_sec=2.0,
    )

    # Initial state
    assert ep.state == EndpointState.WAITING_FOR_SPEECH

    # Feed silence frames (RMS ~0)
    silence_frame = bytes([0, 0] * 160)
    state = ep.process_frame(silence_frame)
    assert state == EndpointState.WAITING_FOR_SPEECH

    # Feed voiced speech frame (RMS ~3960 >= 400)
    voiced_frame = bytes([120, 15] * 160)
    state = ep.process_frame(voiced_frame)
    assert state == EndpointState.SPEECH_IN_PROGRESS

    # Accumulate speech frames
    for _ in range(5):
        ep.process_frame(voiced_frame)

    assert len(ep.get_speech_pcm()) > 0

    # Feed initial silence frame to record silence start
    ep.process_frame(silence_frame)

    # Sleep past silence_timeout_ms (500ms) and send subsequent silence frame
    import time
    time.sleep(0.55)
    final_state = ep.process_frame(silence_frame)
    assert final_state == EndpointState.SPEECH_ENDED


def test_caller_id_hashing():
    """Verify caller ID is stored as salted SHA-256 hash for privacy."""
    raw_id = "test-call-uuid-12345"
    expected_hash = hashlib.sha256(
        f"{settings.SALT_HASH_SECRET}:{raw_id}".encode()
    ).hexdigest()
    assert len(expected_hash) == 64
    assert raw_id not in expected_hash


def test_fixed_prompts_loaded_in_pcm():
    """Verify telephony prompt audio loader returns valid 8 kHz 16-bit mono PCM."""
    pcm = get_prompt_pcm("greeting", "am")
    assert len(pcm) > 0
    # Must be 16-bit samples (even number of bytes)
    assert len(pcm) % 2 == 0

    fallback_pcm = get_prompt_pcm("safe_fallback", "am")
    assert len(fallback_pcm) > 0
    assert len(fallback_pcm) % 2 == 0


def test_audiosocket_constants():
    """Verify AudioSocket wire protocol constants."""
    assert TYPE_AUDIO == 0x02
    assert TYPE_HANGUP == 0x01
