"""Automated test suite for Real Voice Latency Harness & Audio Benchmark (Phase 7 - GAP-03)."""
import io
import wave
from pathlib import Path
import pytest
import soundfile as sf

from eval.stt_benchmark import (
    BENCHMARK_UTTERANCES,
    calculate_cer,
    calculate_wer,
    levenshtein_distance,
    normalize_english_for_eval,
    prepare_audio_conditions,
)
from backend.app.text.amharic import normalize_amharic_for_eval
from backend.app.text.oromo import normalize_oromo_for_eval
from backend.app.pipeline import SessionState, process_utterance

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = WORKSPACE_ROOT / "backend" / "cache" / "prompts"


def test_benchmark_utterances_reference_existing_real_audio():
    """Verify GAP-03: Every utterance in the benchmark harness maps to a real audio file."""
    assert len(BENCHMARK_UTTERANCES) >= 10, "Benchmark dataset should contain at least 10 items"

    for item in BENCHMARK_UTTERANCES:
        audio_file = item["audio_file"]
        file_path = PROMPTS_DIR / audio_file
        assert file_path.exists(), f"Audio file {audio_file} does not exist in {PROMPTS_DIR}"

        # Verify that it is a valid WAV audio file
        data, sr = sf.read(str(file_path))
        assert len(data) > 0, f"Audio file {audio_file} is empty"
        assert sr in (8000, 16000), f"Audio file {audio_file} has unexpected sample rate {sr}"
        assert item["text"].strip(), f"Utterance {item['id']} has empty reference transcript"


def test_prepare_audio_conditions_formats_and_resampling():
    """Verify GAP-03: prepare_audio_conditions creates valid 16k Clean, 8k Narrowband, and G.711 WAV audio."""
    sample_wav = PROMPTS_DIR / "ask_problem_am.wav"
    assert sample_wav.exists()

    conditions = prepare_audio_conditions(sample_wav)

    assert "16k_clean" in conditions
    assert "8k_narrowband" in conditions
    assert "g711_telephony" in conditions

    # 1. Verify 16k Clean WAV format
    with wave.open(io.BytesIO(conditions["16k_clean"]), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000

    # 2. Verify 8k Narrowband WAV format
    with wave.open(io.BytesIO(conditions["8k_narrowband"]), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 8000

    # 3. Verify G.711 Telephony WAV format
    with wave.open(io.BytesIO(conditions["g711_telephony"]), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 8000


def test_levenshtein_distance_and_error_rate_calculations():
    """Verify exact mathematical behavior of WER, CER, and Levenshtein edit distance."""
    # Identity
    assert levenshtein_distance(["a", "b"], ["a", "b"]) == 0
    assert calculate_wer("የጤፍ ሰብል", "የጤፍ ሰብል") == 0.0
    assert calculate_cer("ጤፍ", "ጤፍ") == 0.0

    # Single substitution (1 out of 4 words = 0.25)
    ref = "ዛሬ በምን የግብርና ችግር"
    hyp = "ዛሬ በምን የሰብል ችግር"
    assert calculate_wer(ref, hyp) == 0.25

    # Single deletion (1 out of 4 words = 0.25)
    hyp_del = "ዛሬ በምን የግብርና"
    assert calculate_wer(ref, hyp_del) == 0.25

    # Single insertion
    hyp_ins = "ዛሬ በምን የግብርና ችግር ልርዳዎ"
    # distance is 1, len(ref) is 4 -> 0.25
    assert calculate_wer(ref, hyp_ins) == 0.25

    # Completely disjoint
    assert calculate_wer("አንድ ሁለት", "ሶስት አራት") == 1.0

    # Empty cases
    assert calculate_wer("", "") == 0.0
    assert calculate_wer("", "ቃል") == 1.0
    assert calculate_wer("ቃል", "") == 1.0


def test_orthographic_normalization_impact_on_error_rates():
    """Verify that Amharic Ge'ez homophone folding and Oromo case standardization resolve orthographic variance."""
    # Amharic: ሐ vs ሀ and ፀ vs ጸ
    ref_am = "ፀሐይ በሀረር ወጣ"
    hyp_am = "ጸሀይ በሐረር ወጣ"

    raw_wer = calculate_wer(ref_am, hyp_am)
    assert raw_wer > 0.0, "Raw WER should detect the character difference"

    norm_ref = normalize_amharic_for_eval(ref_am)
    norm_hyp = normalize_amharic_for_eval(hyp_am)
    norm_wer = calculate_wer(norm_ref, norm_hyp)
    assert norm_wer == 0.0, "Normalized WER must fold ሐ->ሀ and ፀ->ጸ"

    # Afaan Oromo: casing and glottal apostrophes
    ref_om = "Baalli Xaafii Keelloo Ta'eera"
    hyp_om = "baalli xaafii keelloo taeera"

    om_raw_wer = calculate_wer(ref_om, hyp_om)
    assert om_raw_wer > 0.0

    om_norm_ref = normalize_oromo_for_eval(ref_om)
    om_norm_hyp = normalize_oromo_for_eval(hyp_om)
    assert normalize_english_for_eval(om_norm_ref) == normalize_english_for_eval(om_norm_hyp)


@pytest.mark.asyncio
async def test_process_utterance_records_stt_latency_when_audio_provided():
    """Verify that process_utterance ingests real audio bytes and records STT latency in metadata."""
    sample_wav = PROMPTS_DIR / "goodbye_am.wav"
    assert sample_wav.exists()

    with open(sample_wav, "rb") as f:
        audio_bytes = f.read()

    session = SessionState(
        session_id="test-eval-harness-turn",
        caller_hash="test_hash_harness",
        language="am",
    )

    res = await process_utterance(
        audio_bytes=audio_bytes,
        session=session,
        text_override=None,
        synthesize_audio=False,
    )

    assert res is not None
    assert "total" in res.metadata.latency_ms
    assert "stt" in res.metadata.latency_ms
    assert res.metadata.latency_ms["stt"] >= 0.0
