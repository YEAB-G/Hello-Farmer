"""Automated tests for STT Verification & Mock Removal (Phase 3)."""
import io
import wave
import numpy as np
import pytest

from app.audio.preprocess import preprocess_speech_for_stt
from app.stt import get_stt_provider
from app.stt.base import Transcript
from app.stt.hf_stt import HuggingFaceSTTProvider
from app.stt.router_stt import MultilingualSTTRouter
from app.stt.whisper_local import WhisperLocalSTTProvider


def generate_synthetic_pcm_8k(duration_sec: float = 0.5, freq: float = 440.0) -> bytes:
    """Generate raw 8kHz 16-bit linear mono PCM audio bytes."""
    sample_rate = 8000
    n_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    # Sine wave tone
    tone = (np.sin(2 * np.pi * freq * t) * 16384).astype(np.int16)
    return tone.tobytes()


@pytest.mark.asyncio
async def test_whisper_local_never_returns_fake_transcript_when_uninitialized():
    """Verify GAP-01 & Rule 8: WhisperLocalSTTProvider returns empty transcript on failure, never fake text."""
    provider = WhisperLocalSTTProvider(model_size="tiny", device="cpu")
    # Ensure model is None
    provider.model = None
    provider._force_uninitialized = True

    audio_8k = generate_synthetic_pcm_8k(duration_sec=0.2)
    transcript = await provider.transcribe(audio_8k, language="am")

    assert isinstance(transcript, Transcript)
    # Non-Negotiable Rule 8: NEVER return canned or fake agricultural statements
    assert transcript.text == "", "Mock transcript was returned instead of empty text!"
    assert transcript.confidence == 0.0
    assert "fake" not in transcript.text
    assert "ጤፍ" not in transcript.text
    assert "Baalli" not in transcript.text
    assert transcript.error is not None


def test_telephony_audio_upsampling_8k_to_16k_wav():
    """Verify GAP-02: 8kHz AudioSocket PCM is cleanly upsampled to 16kHz WAV."""
    raw_8k = generate_synthetic_pcm_8k(duration_sec=0.5, freq=300.0)
    assert len(raw_8k) == 8000  # 0.5s * 8000 samples/s * 2 bytes/sample = 8000 bytes

    wav_16k_bytes = preprocess_speech_for_stt(raw_8k, is_8k_pcm=True)
    assert wav_16k_bytes.startswith(b"RIFF")

    # Read back WAV container to verify metadata and sample rate
    with wave.open(io.BytesIO(wav_16k_bytes), "rb") as wf:
        assert wf.getnchannels() == 1, "Expected mono channel"
        assert wf.getsampwidth() == 2, "Expected 16-bit audio"
        assert wf.getframerate() == 16000, "Audio was not upsampled to 16000 Hz!"
        frames = wf.readframes(wf.getnframes())
        assert len(frames) > 0


@pytest.mark.asyncio
async def test_hohe_stt_empty_audio_handling():
    """Verify that HuggingFaceSTTProvider returns empty transcript for minimal/empty audio."""
    provider = HuggingFaceSTTProvider()
    
    # 1. Zero bytes
    res_empty = await provider.transcribe(b"")
    assert res_empty.text == ""
    assert res_empty.confidence == 0.0
    assert res_empty.provider == "hf_empty"

    # 2. Ultra-short chunk (<800 bytes)
    res_short = await provider.transcribe(b"\x00" * 200)
    assert res_short.text == ""
    assert res_short.confidence == 0.0


@pytest.mark.asyncio
async def test_hohe_stt_transcription_pipeline_mock_execution():
    """Verify local Hohe pipeline text parsing, tag stripping, and confidence assignment."""
    provider = HuggingFaceSTTProvider(token="test_token")

    # Mock the internal pipeline
    def mock_pipeline(wav_bytes):
        return {"text": "[AMH] ጤፍ መዝራት ማዳበሪያ አጠቃቀም"}

    provider._get_local_pipeline = lambda: mock_pipeline

    audio_8k = generate_synthetic_pcm_8k(duration_sec=0.5)
    res = await provider.transcribe(audio_8k, language="am")

    assert res.text == "ጤፍ መዝራት ማዳበሪያ አጠቃቀም", "Language tag [AMH] was not properly stripped!"
    assert res.confidence >= 0.90
    assert res.provider == "hohe_local"
    assert res.model == "snapwre/hohe-asr-amharic"


def test_stt_provider_factory_routing():
    """Verify that get_stt_provider resolves Hohe, Whisper, and Multilingual router appropriately."""
    hohe_prov = get_stt_provider("hohe")
    assert isinstance(hohe_prov, HuggingFaceSTTProvider)

    hf_prov = get_stt_provider("hf")
    assert isinstance(hf_prov, HuggingFaceSTTProvider)

    whisper_prov = get_stt_provider("whisper_local")
    assert isinstance(whisper_prov, WhisperLocalSTTProvider)

    multi_prov = get_stt_provider("multilingual")
    assert isinstance(multi_prov, MultilingualSTTRouter)

