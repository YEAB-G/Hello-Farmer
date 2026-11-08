"""Pre-rendered prompt audio loader for Asterisk telephony.

Loads and caches pre-rendered 8 kHz 16-bit mono linear PCM prompt audio
from backend/cache/prompts/ for zero-latency telephony playback.
"""
from pathlib import Path
import soundfile as sf

PROMPT_CACHE: dict[str, bytes] = {}
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "cache" / "prompts"


def _preload_prompts():
    """Pre-load all prompt wavs into memory on startup for 0ms telephony latency."""
    if not PROMPTS_DIR.exists():
        return
    for wav_file in PROMPTS_DIR.glob("*.wav"):
        try:
            name_stem = wav_file.stem
            data, sr = sf.read(str(wav_file), dtype="int16")
            pcm_bytes = data.tobytes()
            PROMPT_CACHE[name_stem] = pcm_bytes
            # Also register under name without lang if applicable
            parts = name_stem.rsplit("_", 1)
            if len(parts) == 2 and parts[1] in ("am", "om", "en", "ti", "so"):
                PROMPT_CACHE[f"{parts[0]}_{parts[1]}"] = pcm_bytes
        except Exception:
            pass


_preload_prompts()


def get_prompt_pcm(name: str, language: str = "am") -> bytes:
    """Retrieve raw 8 kHz 16-bit mono linear PCM audio bytes for a prompt.

    Args:
        name: Prompt name key (e.g. 'greeting', 'consent', 'one_moment', 'ask_problem', 'goodbye', 'error')
        language: 'am', 'om', 'en', 'ti', 'so'

    Returns:
        Raw 8 kHz 16-bit signed linear mono PCM bytes ready for AudioSocket streaming.
    """
    key = f"{name}_{language}"
    if key in PROMPT_CACHE:
        return PROMPT_CACHE[key]

    # Check Amharic fallback
    am_key = f"{name}_am"
    if am_key in PROMPT_CACHE:
        return PROMPT_CACHE[am_key]

    if name in PROMPT_CACHE:
        return PROMPT_CACHE[name]

    # Target filename on disk if not preloaded
    filename = f"{name}_{language}.wav"
    filepath = PROMPTS_DIR / filename

    if not filepath.exists():
        filepath = PROMPTS_DIR / f"{name}_am.wav"
        if not filepath.exists():
            filepath = PROMPTS_DIR / f"{name}.wav"
            if not filepath.exists():
                if name.startswith("greeting"):
                    filepath = PROMPTS_DIR / "greeting_bilingual.wav"
                else:
                    filepath = None

    if filepath and filepath.exists():
        try:
            data, sr = sf.read(str(filepath), dtype="int16")
            pcm_bytes = data.tobytes()
            PROMPT_CACHE[key] = pcm_bytes
            return pcm_bytes
        except Exception:
            return b""

    return b""
