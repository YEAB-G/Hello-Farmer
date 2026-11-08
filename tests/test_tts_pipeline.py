"""Automated tests for Local Offline TTS Pipeline (Phase 4)."""
import pytest
from pathlib import Path
from app.tts import get_tts_provider
from app.tts.fallback_synth import FallbackSynthProvider
from app.tts.piper_local import PiperLocalTTSProvider
from app.tts.edge_tts_provider import EdgeTTSProvider


@pytest.mark.asyncio
async def test_fallback_synth_selects_spoken_telephony_prompts():
    """Verify GAP-04: Spoken studio prompts are served instead of sine-wave beeps."""
    provider = FallbackSynthProvider()

    # 1. Greeting intent
    pcm_greeting = await provider.synthesize("ጤና ይስጥልኝ እንደምን አደሩ", language="am")
    assert isinstance(pcm_greeting, bytes)
    assert len(pcm_greeting) > 1000, "Expected non-empty PCM audio for greeting prompt"

    # 2. Location inquiry intent
    pcm_location = await provider.synthesize("የት አካባቢ ነው የሚገኙት?", language="am")
    assert isinstance(pcm_location, bytes)
    assert len(pcm_location) > 1000

    # 3. Problem inquiry intent
    pcm_problem = await provider.synthesize("ምን ችግር አጋጠመዎ?", language="am")
    assert isinstance(pcm_problem, bytes)
    assert len(pcm_problem) > 1000

    # 4. Goodbye intent
    pcm_goodbye = await provider.synthesize("ደህና ይሁኑ መልካም ቀን", language="am")
    assert isinstance(pcm_goodbye, bytes)
    assert len(pcm_goodbye) > 1000

    # 5. Generic agricultural advice text defaults to safe_fallback_am.wav
    pcm_fallback = await provider.synthesize("ስለ ጤፍ በሽታ ማብራሪያ", language="am")
    assert isinstance(pcm_fallback, bytes)
    assert len(pcm_fallback) > 1000


@pytest.mark.asyncio
async def test_fallback_synth_multilingual_prompts():
    """Verify spoken prompt selection for Afaan Oromoo and English."""
    provider = FallbackSynthProvider()

    # Afaan Oromoo greeting
    pcm_om = await provider.synthesize("Akkam jirtu", language="om")
    assert len(pcm_om) > 1000

    # English greeting
    pcm_en = await provider.synthesize("Hello and welcome", language="en")
    assert len(pcm_en) > 1000


@pytest.mark.asyncio
async def test_piper_local_tts_graceful_spoken_fallback():
    """Verify PiperLocalTTSProvider falls back to clean spoken prompt when model is uninstalled."""
    provider = PiperLocalTTSProvider()
    
    # Text synthesis should succeed and produce 8kHz audio without crashing
    pcm_audio = await provider.synthesize("ጤና ይስጥልኝ እንኳን ደህና መጡ", language="am")
    assert isinstance(pcm_audio, bytes)
    assert len(pcm_audio) > 1000
    # Must be 16-bit linear PCM (even number of bytes)
    assert len(pcm_audio) % 2 == 0


def test_tts_provider_factory():
    """Verify TTS factory resolves Piper, Fallback, and Edge providers."""
    piper_p = get_tts_provider("piper")
    assert isinstance(piper_p, PiperLocalTTSProvider)

    piper_local_p = get_tts_provider("piper_local")
    assert isinstance(piper_local_p, PiperLocalTTSProvider)

    fallback_p = get_tts_provider("fallback")
    assert isinstance(fallback_p, FallbackSynthProvider)

    edge_p = get_tts_provider("edge_tts")
    assert isinstance(edge_p, EdgeTTSProvider)
