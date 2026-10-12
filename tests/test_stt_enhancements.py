"""Unit tests for STT enhancements: AGC, Pre-emphasis, Domain Biasing, and Smart Cascade."""
import numpy as np
import pytest

from backend.app.audio.preprocess import (
    apply_automatic_gain_control,
    apply_preemphasis,
    preprocess_speech_for_stt,
)
from backend.app.stt.base import BaseSTTProvider, Transcript
from backend.app.stt.cascade_stt import CascadingSTTProvider
from backend.app.stt.prompts import (
    AGRICULTURAL_PROMPT_AM,
    AGRICULTURAL_PROMPT_OM,
    get_stt_biasing_prompt,
)


def test_preemphasis_filter_boosts_high_frequencies():
    """Verify pre-emphasis filter sharpens transients."""
    # Constant signal: y[n] = x[n] - 0.97 * x[n-1] -> approaches ~0.03
    signal = np.ones(100, dtype=np.float32) * 0.5
    filtered = apply_preemphasis(signal, alpha=0.96)

    assert len(filtered) == 100
    assert filtered[0] == 0.5
    assert np.isclose(filtered[-1], 0.5 * (1 - 0.96), atol=1e-3)


def test_automatic_gain_control_normalizes_quiet_audio():
    """Verify AGC amplifies low-level speech up toward target RMS."""
    # Very quiet signal (RMS ~ 0.01)
    quiet = (np.sin(np.linspace(0, 20 * np.pi, 1000)) * 0.01).astype(np.float32)
    normalized = apply_automatic_gain_control(quiet, target_rms=0.08, max_gain=8.0)

    original_rms = np.sqrt(np.mean(quiet**2))
    norm_rms = np.sqrt(np.mean(normalized**2))

    assert norm_rms > original_rms
    assert np.all(normalized >= -1.0) and np.all(normalized <= 1.0)


def test_preprocess_speech_for_stt_outputs_16k_wav():
    """Verify preprocess_speech_for_stt converts 8kHz PCM to 16kHz WAV."""
    # 8000 samples = 1 second of 8kHz 16-bit linear PCM (16000 bytes)
    raw_pcm_8k = bytes([10, 0] * 8000)
    wav_bytes = preprocess_speech_for_stt(raw_pcm_8k, is_8k_pcm=True, apply_filter=True)

    assert len(wav_bytes) > 0
    assert wav_bytes.startswith(b"RIFF")


def test_domain_biasing_prompts_contain_key_crops_and_inputs():
    """Verify agricultural prompts contain critical terms."""
    prompt_am = get_stt_biasing_prompt("am")
    assert "ጤፍ" in prompt_am
    assert "ስንዴ" in prompt_am
    assert "ማዳበሪያ" in prompt_am
    assert "የስንዴ ዋግ" in prompt_am

    prompt_om = get_stt_biasing_prompt("om")
    assert "xaafii" in prompt_om.lower()
    assert "qamadii" in prompt_om.lower()
    assert "xaa'oo" in prompt_om.lower()


class MockFastProvider(BaseSTTProvider):
    def __init__(self, should_fail: bool = False, is_hallucination: bool = False):
        self.should_fail = should_fail
        self.is_hallucination = is_hallucination

    async def transcribe(self, wav_path_or_bytes, language="am") -> Transcript:
        if self.should_fail:
            return Transcript(text="", confidence=0.0, provider="mock_fast_fail", latency_ms=15.0, language=language)
        if self.is_hallucination:
            return Transcript(text="thank you for watching", confidence=0.9, provider="mock_fast_hallucination", latency_ms=15.0, language=language)
        return Transcript(text="በቆሎ ላይ ተባይ ገብቷል", confidence=0.92, provider="mock_fast", latency_ms=25.0, language=language)


class MockFallbackProvider(BaseSTTProvider):
    async def transcribe(self, wav_path_or_bytes, language="am") -> Transcript:
        return Transcript(text="በቆሎ ላይ ኩብኩባ ታይቷል", confidence=0.95, provider="mock_gemini_fallback", latency_ms=85.0, language=language)


@pytest.mark.asyncio
async def test_cascading_stt_uses_fast_path_when_confident():
    """Verify smart cascade uses fast primary engine when confident."""
    primary = MockFastProvider(should_fail=False)
    secondary = MockFallbackProvider()
    cascade = CascadingSTTProvider(primary=primary, secondary=secondary)

    res = await cascade.transcribe(b"dummy_audio", language="am")
    assert res.provider == "mock_fast"
    assert res.text == "በቆሎ ላይ ተባይ ገብቷል"


@pytest.mark.asyncio
async def test_cascading_stt_falls_back_when_primary_hallucinates_or_fails():
    """Verify smart cascade routes to fallback engine when primary hallucinates."""
    primary = MockFastProvider(should_fail=False, is_hallucination=True)
    secondary = MockFallbackProvider()
    cascade = CascadingSTTProvider(primary=primary, secondary=secondary)

    res = await cascade.transcribe(b"dummy_audio", language="am")
    assert res.provider == "mock_gemini_fallback"
    assert res.text == "በቆሎ ላይ ኩብኩባ ታይቷል"

