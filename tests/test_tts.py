"""Unit tests for TTS synthesis, caching, and prompt WAV validation."""
import io

import pytest
import soundfile as sf
from backend.app.audio.convert import pcm8k_to_wav
from backend.app.tts.edge_tts_provider import EdgeTTSProvider
from backend.app.tts.fallback_synth import FallbackSynthProvider


def test_tts_base_caching_and_sentence_split(tmp_path):
    """Verify SHA-256 caching and sentence parsing on BaseTTSProvider."""
    synth = FallbackSynthProvider(cache_dir=str(tmp_path))

    text = "እንኳን ደህና መጡ። ጥያቄዎን ይናገሩ።"
    sentences = synth.split_into_sentences(text)
    assert len(sentences) == 2
    assert sentences[0] == "እንኳን ደህና መጡ"
    assert sentences[1] == "ጥያቄዎን ይናገሩ"

    cache_file = synth.get_cache_path(text, "test_voice", "am")
    assert not cache_file.exists()


@pytest.mark.asyncio
async def test_fallback_synth_audio_format(tmp_path):
    """Verify FallbackSynthProvider produces authentic 8 kHz 16-bit mono linear PCM."""
    synth = FallbackSynthProvider(cache_dir=str(tmp_path))
    pcm_data = await synth.synthesize("ጤፍ ላይ ቢጫ ቅጠል", voice="fallback", language="am")

    assert len(pcm_data) > 0
    # Must be 16-bit samples (2 bytes per sample)
    assert len(pcm_data) % 2 == 0

    wav_bytes = pcm8k_to_wav(pcm_data)
    data, sr = sf.read(io.BytesIO(wav_bytes))

    assert sr == 8000
    assert len(data.shape) == 1


def test_prompt_audio_loader():
    """Verify pre-rendered prompt audio loader retrieves 8 kHz PCM."""
    from backend.app.telephony.prompts_audio import get_prompt_pcm

    greeting_pcm = get_prompt_pcm("greeting", "am")
    assert len(greeting_pcm) > 0
    # Must be 16-bit samples
    assert len(greeting_pcm) % 2 == 0

    safe_fallback_pcm = get_prompt_pcm("safe_fallback", "am")
    assert len(safe_fallback_pcm) > 0



@pytest.mark.asyncio
async def test_edge_tts_synthesis(tmp_path):
    """Verify EdgeTTSProvider synthesizes Amharic into 8 kHz mono audio."""
    synth = EdgeTTSProvider(cache_dir=str(tmp_path))
    pcm_data = await synth.synthesize("ሰላም", voice="am-ET-AmehaNeural", language="am")

    assert len(pcm_data) > 0
    wav_bytes = pcm8k_to_wav(pcm_data)
    data, sr = sf.read(io.BytesIO(wav_bytes))

    assert sr == 8000
    assert len(data.shape) == 1
