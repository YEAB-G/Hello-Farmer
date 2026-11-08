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
try:
    from backend.app.tts.gemini_tts_provider import GeminiTTSProvider
    from backend.app.tts.edge_tts_provider import EdgeTTSProvider
except ImportError:
    from app.tts.gemini_tts_provider import GeminiTTSProvider
    from app.tts.edge_tts_provider import EdgeTTSProvider

PROMPTS_SPEC = {
    # ----------------------------------------------------
    # Amharic Prompts (Gemini TTS Voice: Kore)
    # ----------------------------------------------------
    "greeting_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "rate": "-15%",
        "text": "ሰላም፣ ወደ ሄሎ ፋርመር እንኳን ደህና መጡ። አገልግሎታችንን ለማሻሻል፣ ይህ ጥሪ እየተቀዳ ነው።",
    },
    "ask_location_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "rate": "-13%",
        "text": "ከየትኛው አካባቢ ነው የሚደውሉት?",
    },
    "greeting_location_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "rate": "-15%",
        "text": "ሰላም፣ ወደ ሄሎ ፋርመር እንኳን ደህና መጡ። ከየትኛው አካባቢ ነው የሚደውሉት?",
    },
    "clarify_region_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "rate": "-13%",
        "text": "በየትኛው ክልል ውስጥ ነው?",
    },
    "ask_problem_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "text": "ዛሬ በምን የግብርና ችግር ልርዳዎ?",
    },
    "repeat_prompt_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "text": "ይቅርታ፣ አልተሰማኝም። እባክዎ ጥያቄዎን በድጋሚ ይናገሩ።",
    },
    "safe_fallback_am.wav": {
        "lang": "am",
        "voice": "Kore",
        "text": "ይቅርታ፣ ለዚህ ጥያቄ የተረጋገጠ መረጃ አላገኘሁም። እባክዎ የአካባቢዎን የግብርና ልማት ጣቢያ ባለሙያ ያማክሩ ወይም በስምንት ዜሮ ሁለት ስምንት ይደውሉ።",
    },
    "goodbye_am.wav": {
        "lang": "am",
        "voice": "am-ET-MekdesNeural",
        "text": "ስለደወሉ እናመሰግናለን። ደህና ይሁኑ።",
    },
    "anything_else_am.wav": {
        "lang": "am",
        "voice": "am-ET-MekdesNeural",
        "text": "ሌላ የምረዳዎት የግብርና ጥያቄ አለዎት?",
    },
    "one_moment_am.wav": {
        "lang": "am",
        "voice": "am-ET-MekdesNeural",
        "text": "እባክዎ ትንሽ ይጠብቁ፣ መረጃውን እየፈለግሁ ነው።",
    },
    "still_checking_am.wav": {
        "lang": "am",
        "voice": "am-ET-MekdesNeural",
        "text": "አሁንም ከግብርና መመሪያው እያጣራሁ ነው፣ ጥቂት ሰከንድ ይታገሱ።",
    },
    "listening_reminder_am.wav": {
        "lang": "am",
        "voice": "am-ET-MekdesNeural",
        "text": "እየሰማሁዎት ነው፣ እባክዎ ጥያቄዎን ይናገሩ።",
    },
    "error_am.wav": {
        "lang": "am",
        "voice": "am-ET-MekdesNeural",
        "text": "ይቅርታ፣ የቴክኒክ ችግር አጋጥሟል። እባክዎ ቆየት ብለው ይደውሉ።",
    },

    # ----------------------------------------------------
    # Afaan Oromo Prompts (Gemini TTS Voice: Kore)
    # ----------------------------------------------------
    "greeting_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Akkam, baga gara Hello Farmer nagaan dhuftan. Tajaajila keenya fooyyessuuf wamichi kun waraabamaa jira.",
    },
    "ask_location_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Naannoo kam irraa bilbilaa jirtu?",
    },
    "greeting_location_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Naannoo kam irraa bilbilaa jirtu?",
    },
    "clarify_region_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Naannoo kam keessatti argama?",
    },
    "ask_problem_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Har'a rakkoo qonnaa maaliin isin gargaaruu danda'a?",
    },
    "repeat_prompt_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Dhiifama, hin dhagahamne. Maaloo irra deebi'aa dubbadhaa.",
    },
    "safe_fallback_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Dhiifama, gaaffii kanaaf ragaan gahaan hin jiru. Maaloo ogeessa qonnaa naannoo keessanii gaafadhaa yookiin saddeet-duwwaa-lama-saddeet irratti bilbilaa.",
    },
    "goodbye_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Waan bilbiltaniif galatoomaa. Nagaatti.",
    },
    "anything_else_om.wav": {
        "lang": "om",
        "voice": "am-ET-MekdesNeural",
        "text": "Gaaffii qonnaa biraa isin gargaaruu danda'u qabduu?",
    },
    "one_moment_om.wav": {
        "lang": "om",
        "voice": "am-ET-MekdesNeural",
        "text": "Maaloo yeroo gabaabaaf eegaa, odeeffannoo barbaadaa jira.",
    },
    "still_checking_om.wav": {
        "lang": "om",
        "voice": "am-ET-MekdesNeural",
        "text": "Ammas ragaa qonnaa keessaa ilaalaa jira, maaloo xiqqoo na eegaa.",
    },
    "listening_reminder_om.wav": {
        "lang": "om",
        "voice": "am-ET-MekdesNeural",
        "text": "Isin dhaggeeffachaan jira, maaloo gaaffii keessan dubbadhaa.",
    },
    "error_om.wav": {
        "lang": "om",
        "voice": "Kore",
        "text": "Dhiifama, rakkoon teeknikaa mudateera. Maaloo booda bilbilaa.",
    },

    # ----------------------------------------------------
    # English Prompts
    # ----------------------------------------------------
    "greeting_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Hello, welcome to Hello Farmer. This call is being recorded to improve our service.",
    },
    "ask_location_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Which area are you calling from?",
    },
    "greeting_location_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Which area are you calling from?",
    },
    "clarify_region_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Which region is that in?",
    },
    "ask_problem_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "What farming problem can I help you with today?",
    },
    "repeat_prompt_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Sorry, I could not hear you clearly. Please repeat your question.",
    },
    "safe_fallback_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Sorry, there is no verified information available for this query. Please consult your local agricultural development agent or call eight zero two eight.",
    },
    "goodbye_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Thank you for calling Hello Farmer. Goodbye.",
    },
    "anything_else_en.wav": {
        "lang": "en",
        "voice": "en-US-JennyNeural",
        "text": "Do you have any other farming question I can help you with?",
    },
    "one_moment_en.wav": {
        "lang": "en",
        "voice": "en-US-JennyNeural",
        "text": "Please hold on for a moment while I retrieve the information.",
    },
    "still_checking_en.wav": {
        "lang": "en",
        "voice": "en-US-JennyNeural",
        "text": "Still checking the agricultural manual for you, one moment please.",
    },
    "listening_reminder_en.wav": {
        "lang": "en",
        "voice": "en-US-JennyNeural",
        "text": "I am listening, please feel free to ask your question.",
    },
    "error_en.wav": {
        "lang": "en",
        "voice": "Kore",
        "text": "Sorry, a technical error occurred. Please call back later.",
    },
    # Bilingual Initial Greeting (Unified with Kore)
    "greeting_bilingual.wav": {
        "lang": "am",
        "voice": "Kore",
        "rate": "-15%",
        "text": "ሰላም፣ ወደ ሄሎ ፋርመር እንኳን ደህና መጡ። Baga gara Heelo Faarmar nagaan dhuftan.",
    },
}


import argparse


async def render_prompts(lang_filter: str = "all", target_dir: str = "backend/cache/prompts"):
    print("=" * 80)
    print("HELLO FARMER: RENDERING FIXED TELEPHONY PROMPT WAVs (GEMINI-FIRST)")
    print(f"Filter language: {lang_filter} | Output directory: {target_dir}")
    print("=" * 80)

    prompt_dir = Path(target_dir)
    prompt_dir.mkdir(parents=True, exist_ok=True)

    tts_provider = EdgeTTSProvider(cache_dir="backend/cache/tts")
    success_count = 0

    items_to_render = {
        k: v for k, v in PROMPTS_SPEC.items()
        if lang_filter == "all" or v.get("lang") == lang_filter
    }

    for filename, spec in items_to_render.items():
        out_path = prompt_dir / filename
        try:
            pcm_8k = await tts_provider.synthesize(
                spec["text"],
                voice=None,
                language=spec["lang"],
                rate=spec.get("rate"),
            )
        except Exception as e:
            print(f"  ✗ TTS synthesis error for {filename}: {e}")
            pcm_8k = None

        if pcm_8k:
            wav_data = pcm8k_to_wav(pcm_8k)
            out_path.write_bytes(wav_data)
            duration_s = len(pcm_8k) / (8000 * 2)
            print(f"  ✓ Rendered {filename:<25} ({duration_s:4.2f}s, {len(wav_data)} bytes)")
            success_count += 1
        else:
            print(f"  ✗ Failed to render {filename}")

    print("-" * 80)
    print(f"Successfully rendered {success_count} / {len(items_to_render)} prompts.")
    print(f"Prompts stored at: {prompt_dir}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render Hello Farmer telephony prompts")
    parser.add_argument("--lang", choices=["am", "om", "all"], default="all", help="Language filter")
    parser.add_argument("--output-dir", default="backend/cache/prompts", help="Destination prompt directory")
    args = parser.parse_args()

    asyncio.run(render_prompts(lang_filter=args.lang, target_dir=args.output_dir))

