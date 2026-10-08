"""Baseline Phase 0 tests for Hello Farmer."""
import struct

import numpy as np
import pytest
from backend.app.audio.convert import (
    float32_to_pcm,
    pcm8k_to_pcm16k,
    pcm16k_to_pcm8k,
    pcm_to_float32,
)
from backend.app.config import load_yaml_config, settings
from backend.app.database.models import Base
from backend.app.pipeline import SessionState, process_utterance
from backend.app.telephony.audiosocket_server import TYPE_AUDIO


def test_config_loads():
    """Verify settings and YAML configuration load correctly."""
    assert settings.AUDIOSOCKET_PORT == 9092
    assert settings.BARGE_IN_ENABLED is False  # Must remain False by default
    assert settings.CONCURRENCY_LIMIT >= 2

    yaml_data = load_yaml_config()
    assert "telephony" in yaml_data
    assert "audio" in yaml_data


def test_audio_conversion_roundtrip():
    """Verify audio resampling between 8 kHz and 16 kHz."""
    # Create 8000 samples of a 440Hz sine wave at 8 kHz (1 second)
    t8 = np.linspace(0, 1.0, 8000, endpoint=False)
    sine8 = (np.sin(2 * np.pi * 440 * t8) * 32767).astype(np.int16)
    pcm8 = sine8.tobytes()

    # Upsample to 16 kHz
    pcm16 = pcm8k_to_pcm16k(pcm8)
    # Output should have 16000 samples (32000 bytes)
    assert len(pcm16) == 16000 * 2

    # Downsample back to 8 kHz
    pcm8_reconstructed = pcm16k_to_pcm8k(pcm16)
    assert len(pcm8_reconstructed) == 8000 * 2

    # Float conversion
    float_audio = pcm_to_float32(pcm8)
    assert np.all(float_audio <= 1.0) and np.all(float_audio >= -1.0)
    pcm_back = float32_to_pcm(float_audio)
    assert len(pcm_back) == len(pcm8)


def test_audiosocket_protocol_framing():
    """Test standard 3-byte AudioSocket frame construction."""
    payload = b"HelloAudioSocket"
    header = struct.pack("!BH", TYPE_AUDIO, len(payload))
    frame = header + payload

    msg_type, length = struct.unpack("!BH", frame[:3])
    assert msg_type == TYPE_AUDIO
    assert length == len(payload)
    assert frame[3:] == payload


@pytest.mark.asyncio
async def test_pipeline_basic_execution():
    """Verify decoupled process_utterance responds without Asterisk."""
    session = SessionState(
        session_id="test-session-123",
        caller_hash="hash-abc",
        language="am",
    )
    response = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override="የጤፍ በሽታ",
    )
    assert response is not None
    assert len(response.text) > 0
    assert response.metadata is not None


def test_database_models_metadata():
    """Verify SQLAlchemy models define all core tables correctly."""
    tables = Base.metadata.tables.keys()
    required_tables = [
        "farmers",
        "farmer_context",
        "farmer_crops",
        "calls",
        "conversation_messages",
        "agricultural_documents",
        "knowledge_chunks",
        "weather_records",
        "warnings",
        "farmer_warnings",
        "sms_messages",
        "web_notifications",
        "ai_interactions",
        "consent_records",
        "place_names",
        "quota_usage",
    ]
    for table in required_tables:
        assert table in tables, f"Missing table {table} in models schema"
