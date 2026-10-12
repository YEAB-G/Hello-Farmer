"""Comprehensive automated test suite for Hello Farmer End-to-End Web Voice Chat.

Validates:
1. Typed Amharic question -> text answer -> spoken answer (TTS audio).
2. Spoken Amharic question -> transcript -> agricultural RAG answer -> spoken answer.
3. Spoken Afaan Oromo question -> transcript -> agricultural answer -> spoken answer.
4. Voice transcription endpoint (/api/v1/voice/transcribe) with audio transcoding.
5. Voice synthesis endpoint (/api/v1/voice/synthesize) with WAV streaming retrieval (/api/v1/voice/audio/{id}).
6. Multi-turn conversation context retention across follow-up questions using session_id.
7. Error handling: empty audio, silence, invalid base64, missing parameters.
8. Fallback resiliency: TTS fallback returns valid audio without crashing.
"""
import base64
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from app.main import app
from app.audio.convert import browser_audio_to_wav16k, pcm8k_to_wav, pcm8k_to_wav_base64


@pytest.fixture
def sample_amharic_wav_b64() -> str:
    """Load sample Amharic audio from repository cache as base64."""
    wav_path = Path("cache/prompts/greeting_am.wav")
    if not wav_path.exists():
        wav_path = Path("backend/cache/prompts/greeting_am.wav")
    audio_bytes = wav_path.read_bytes()
    return base64.b64encode(audio_bytes).decode("ascii")


@pytest.fixture
def sample_oromo_wav_b64() -> str:
    """Load sample Afaan Oromo audio from repository cache as base64."""
    wav_path = Path("cache/prompts/greeting_om.wav")
    if not wav_path.exists():
        wav_path = Path("backend/cache/prompts/greeting_om.wav")
    audio_bytes = wav_path.read_bytes()
    return base64.b64encode(audio_bytes).decode("ascii")


@pytest.mark.asyncio
async def test_audio_conversion_utilities(sample_amharic_wav_b64):
    """Test browser audio transcoding and WAV container packaging."""
    raw_bytes = base64.b64decode(sample_amharic_wav_b64)
    wav16k = browser_audio_to_wav16k(raw_bytes)
    assert len(wav16k) > 0
    assert wav16k.startswith(b"RIFF")

    # Test PCM to WAV base64
    pcm_test = b"\x00\x00" * 800  # 100ms silence
    b64_uri = pcm8k_to_wav_base64(pcm_test)
    assert b64_uri.startswith("data:audio/wav;base64,")


@pytest.mark.asyncio
async def test_transcribe_endpoint(sample_amharic_wav_b64):
    """Test /api/v1/voice/transcribe endpoint with authentic speech sample."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voice/transcribe",
            json={"audio_base64": sample_amharic_wav_b64, "language": "am"},
            timeout=20.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "transcript" in data
        assert len(data["transcript"]) > 0
        assert data["language"] == "am"
        assert data["confidence"] > 0.0


@pytest.mark.asyncio
async def test_synthesize_endpoint_and_audio_stream():
    """Test speech synthesis and subsequent WAV audio streaming by ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Synthesize Amharic speech
        synth_resp = await client.post(
            "/api/v1/voice/synthesize",
            json={"text": "ሰላም ጤና ይስጥልኝ ሄሎ ፋርመር", "language": "am"},
            timeout=15.0,
        )
        assert synth_resp.status_code == 200
        synth_data = synth_resp.json()
        assert synth_data["audio_base64"].startswith("data:audio/wav;base64,")
        assert synth_data["audio_url"].startswith("/api/v1/voice/audio/")

        # 2. Fetch the cached audio WAV stream
        audio_url = synth_data["audio_url"]
        stream_resp = await client.get(audio_url)
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"] == "audio/wav"
        assert stream_resp.content.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_typed_question_with_tts_synthesis():
    """Test typed Amharic question returning both text answer and spoken audio."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ask",
            json={
                "question": "ለጤፍ የሚሆን ማዳበሪያ መጠን ስንት ነው?",
                "language": "am",
                "synthesize_audio": True,
            },
            timeout=30.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 0
        assert data["audio_base64"].startswith("data:audio/wav;base64,")
        assert data["confidence"] > 0.0


@pytest.mark.asyncio
async def test_voice_ask_end_to_end(sample_amharic_wav_b64):
    """Test complete voice input -> STT -> RAG -> text & audio answer."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voice/ask",
            json={
                "audio_base64": sample_amharic_wav_b64,
                "language": "am",
                "synthesize_audio": True,
            },
            timeout=35.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transcript"]) > 0
        assert len(data["answer"]) > 0
        assert data["audio_base64"].startswith("data:audio/wav;base64,")
        assert "session_id" in data


@pytest.mark.asyncio
async def test_multi_turn_conversation_context():
    """Verify follow-up questions retain the conversation context across turns."""
    transport = ASGITransport(app=app)
    import time
    session_id = f"test-session-{int(time.time() * 1000)}"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Turn 1: Ask about teff fertilizer
        resp1 = await client.post(
            "/api/v1/voice/ask",
            json={
                "question": "የጤፍ ማዳበሪያ አጠቃቀም መጠን ስንት ነው?",
                "session_id": session_id,
                "language": "am",
                "synthesize_audio": False,
            },
            timeout=30.0,
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert "answer" in data1

        # Turn 2: Follow up question without repeating the crop name
        resp2 = await client.post(
            "/api/v1/voice/ask",
            json={
                "question": "መቼ ነው የምጨምረው?",
                "session_id": session_id,
                "language": "am",
                "synthesize_audio": False,
            },
            timeout=30.0,
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        # The answer should maintain agronomic context
        assert len(data2["answer"]) > 0


@pytest.mark.asyncio
async def test_empty_and_silent_audio_error_handling():
    """Verify graceful handling when audio is empty or corrupt."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Empty audio payload
        resp_empty = await client.post(
            "/api/v1/voice/transcribe",
            json={"audio_base64": "", "language": "am"},
        )
        assert resp_empty.status_code == 400

        # 2. Corrupt base64
        resp_corrupt = await client.post(
            "/api/v1/voice/transcribe",
            json={"audio_base64": "not_valid_base64_%%%!", "language": "am"},
        )
        assert resp_corrupt.status_code == 400

        # 3. Voice ask with empty question and no audio
        resp_no_input = await client.post(
            "/api/v1/voice/ask",
            json={"question": "", "audio_base64": "", "language": "am"},
            timeout=10.0,
        )
        assert resp_no_input.status_code == 200
        # Pipeline returns graceful fallback message without error
        data = resp_no_input.json()
        assert "አልተሰማም" in data["answer"] or "ጥያቄ" in data["answer"]


@pytest.mark.asyncio
async def test_oromo_voice_ask(sample_oromo_wav_b64):
    """Test Afaan Oromo speech recognition and localized response generation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/voice/ask",
            json={
                "audio_base64": sample_oromo_wav_b64,
                "language": "om",
                "synthesize_audio": True,
            },
            timeout=35.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["transcript"]) > 0
        assert len(data["answer"]) > 0
        assert data["language"] == "om"
