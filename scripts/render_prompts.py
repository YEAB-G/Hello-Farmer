"""Pre-render all fixed telephony prompt audio files.

Pre-renders prompts once into 8 kHz 16-bit mono linear PCM WAV files in
backend/cache/prompts/ so fixed prompts are never synthesized dynamically during calls.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.audio.convert import pcm8k_to_wav
from backend.app.tts.edge_tts_provider import EdgeTTSProvider

PROMPTS_SPEC = {
    # Amharic Prompts
    "greeting_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "እንኳን ወደ ሄሎ ፋርመር የሙከራ የግብርና ረዳት በደህና መጡ። ጥያቄዎን በቀጥታ መናገር ይችላሉ።",
    },
    "consent_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "ይህ አገልግሎት እንዲሻሻል ጥያቄዎ እንዲቀመጥ ይፈቅዳሉ?",
    },
    "one_moment_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "እባክዎ ትንሽ ይጠብቁ...",
    },
    "low_confidence_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "ይቅርታ፣ ድምጽዎ በደንብ አልተሰማም። እባክዎ ጥያቄዎን በድጋሚ ይናገሩ።",
    },
    "safe_fallback_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "ይቅርታ፣ ለዚህ ጥያቄ በቂ የተረጋገጠ መረጃ አላገኘሁም። እባክዎ የአካባቢዎን የግብርና ልማት ጣቢያ ባለሙያ ያማክሩ ወይም በስምንት ዜሮ ሁለት ስምንት ይደውሉ።",
    },
    "goodbye_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "ስለደወሉ እናመሰግናለን። ደህና ይሁኑ።",
    },
    "error_am.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "ይቅርታ፣ የስርዓት መቆራረጥ አጋጥሟል። እባክዎ የአካባቢዎን የግብርና ባለሙያ ያማክሩ።",
    },
    # Afaan Oromo Prompts
    "greeting_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Baga gara gargaaraa qonnaa Heelo Faarmar nagaan dhuftan. Gaaffii keessan kallattiin dubbachuu dandeessu.",
    },
    "consent_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Tajaajilli kun akka fooyya'uuf gaaffiin keessan akka galmaa'u ni eeyyamtuu?",
    },
    "one_moment_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Mee xiqqoo eegaa...",
    },
    "low_confidence_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Dhiifama, sagaleen keessan sirriitti hin dhagahamne. Maaloo irra deebi'aa dubbadhaa.",
    },
    "safe_fallback_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Dhiifama, gaaffii kanaaf ragaan amansiisaan gahaan hin jiru. Maaloo ogeessa misooma qonnaa naannoo keessanii gaafadhaa yookiin bilbila saddeet-duwwaa-lama-saddeet irratti bilbilaa.",
    },
    "goodbye_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Waan bilbiltaniif galatoomaa. Nagaatti.",
    },
    "error_om.wav": {
        "lang": "om",
        "voice": "am-ET-AmehaNeural",
        "text": "Dhiifama, rakkoon teeknikaa mudateera. Maaloo ogeessa qonnaa naannoo keessanii gaafadhaa.",
    },
    # Bilingual Initial Greeting
    "greeting_bilingual.wav": {
        "lang": "am",
        "voice": "am-ET-AmehaNeural",
        "text": "እንኳን ወደ ሄሎ ፋርመር በደህና መጡ። Baga gara Heelo Faarmar nagaan dhuftan.",
    },
}


async def render_prompts():
    print("=" * 80)
    print("HELLO FARMER: RENDERING FIXED TELEPHONY PROMPT WAVs (PHASE 2)")
    print("=" * 80)

    prompt_dir = Path("backend/cache/prompts")
    prompt_dir.mkdir(parents=True, exist_ok=True)

    tts_provider = EdgeTTSProvider(cache_dir="backend/cache/tts")
    success_count = 0

    for filename, spec in PROMPTS_SPEC.items():
        out_path = prompt_dir / filename
        pcm_8k = await tts_provider.synthesize(
            spec["text"],
            voice=spec["voice"],
            language=spec["lang"]
        )

        if pcm_8k:
            wav_data = pcm8k_to_wav(pcm_8k)
            out_path.write_bytes(wav_data)
            duration_s = len(pcm_8k) / (8000 * 2)
            print(f"  ✓ Rendered {filename:<25} ({duration_s:4.2f}s, {len(wav_data)} bytes)")
            success_count += 1
        else:
            print(f"  ✗ Failed to render {filename}")

    print("-" * 80)
    print(f"Successfully rendered {success_count} / {len(PROMPTS_SPEC)} fixed prompts.")
    print(f"Prompts stored at: {prompt_dir}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(render_prompts())
