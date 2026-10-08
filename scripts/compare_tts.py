"""TTS Voice Comparison Script.

Renders 10 standardized agricultural answers through available TTS providers/voices
and exports audio WAVs (8 kHz 16-bit mono) and an evaluation CSV for human rating.
"""
import asyncio
import csv
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.audio.convert import pcm8k_to_wav
from backend.app.tts.edge_tts_provider import EdgeTTSProvider
from backend.app.tts.fallback_synth import FallbackSynthProvider

# 10 Grounded Agricultural Evaluation Answers
TEST_ANSWERS = [
    {
        "id": "ANS-01",
        "lang": "am",
        "topic": "teff_waterlogging",
        "text": "የጤፍ ቅጠል ቢጫ መሆን በውሃ ማቆር ምክንያት ሊከሰት ይችላል። የውሃ መውጫ ቦዮችን በማዘጋጀት ውሃውን ያፍስሱ።",
    },
    {
        "id": "ANS-02",
        "lang": "am",
        "topic": "wheat_yellow_rust",
        "text": "በስንዴ ቅጠል ላይ ቢጫ መስመሮች ከታዩ የቢጫ ዋግ በሽታ ሊሆን ይችላል። መድሃኒት ከመጠቀምዎ በፊት የልማት ጣቢያ ባለሙያ ያማክሩ።",
    },
    {
        "id": "ANS-03",
        "lang": "am",
        "topic": "vertisol_drainage",
        "text": "ጥቁር አፈር ውሃ የመያዝ አቅሙ ከፍተኛ በመሆኑ ሰብል እንዳይታፈን በየጊዜው ቦይ ማውጣት ያስፈልጋል።",
    },
    {
        "id": "ANS-04",
        "lang": "am",
        "topic": "pesticide_safety",
        "text": "ማንኛውንም ፀረ-ተባይ ኬሚካል ሲጠቀሙ ከነፋስ አቅጣጫ በተቃራኒ አይርጩ። የመመረዝ ምልክት ካለ ወዲያውኑ ወደ ጤና ጣቢያ ይሂዱ።",
    },
    {
        "id": "ANS-05",
        "lang": "am",
        "topic": "rainfall_spraying",
        "text": "በሚቀጥሉት ሰዓታት ከባድ ዝናብ ስለሚጠበቅ የኬሚካል ርጭት ቢያቆዩ ይመረጣል። ዝናቡ ኬሚካሉን አጥቦ ሊወስደው ይችላል።",
    },
    {
        "id": "ANS-06",
        "lang": "om",
        "topic": "teff_waterlogging",
        "text": "Baalli xaafii keelloo ta'uun bishaan kuullamuun ta'uu danda'a. Bo'oo lolaa baasuun bishaan dhangalaasaa.",
    },
    {
        "id": "ANS-07",
        "lang": "om",
        "topic": "wheat_yellow_rust",
        "text": "Baala qamadii irratti sararri keelloon yoo mul'ate dhibee waagii ta'uu mala. Ogeessa qonnaa mariisisaa.",
    },
    {
        "id": "ANS-08",
        "lang": "om",
        "topic": "maize_blight",
        "text": "Boqqoolloo irratti dhibeen baalaa yeroo jiidhina ol'aanaa qabu waan ka'uuf ooyiruu keessan yeroo mara to'adhaa.",
    },
    {
        "id": "ANS-09",
        "lang": "om",
        "topic": "pesticide_safety",
        "text": "Qoricha qonnaa yeroo fufan kallattii qilleensaa duraan hin fufinaa. Madda bishaanii irraa fageessaa.",
    },
    {
        "id": "ANS-10",
        "lang": "am",
        "topic": "safe_fallback",
        "text": "ይቅርታ፣ ለዚህ ጥያቄ በቂ የተረጋገጠ መረጃ አላገኘሁም። እባክዎ የአካባቢዎን የግብርና ልማት ጣቢያ ባለሙያ ያማክሩ ወይም በስምንት ዜሮ ሁለት ስምንት ይደውሉ።",
    },
]


async def run_comparison():
    print("=" * 80)
    print("HELLO FARMER: TTS COMPARISON & INTELLIGIBILITY BENCHMARK (PHASE 2)")
    print("=" * 80)

    output_dir = Path("eval/reports/tts_samples")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = Path("eval/reports/tts_comparison.csv")

    providers = [
        ("Edge-TTS (Male)", EdgeTTSProvider(), "am-ET-AmehaNeural"),
        ("Edge-TTS (Female)", EdgeTTSProvider(), "am-ET-MekdesNeural"),
        ("Fallback-Synth", FallbackSynthProvider(), "fallback_acoustic"),
    ]

    records = []
    print(f"Rendering {len(TEST_ANSWERS)} answers across {len(providers)} configurations...")

    for ans in TEST_ANSWERS:
        ans_id = ans["id"]
        lang = ans["lang"]
        text = ans["text"]

        for prov_label, provider, voice in providers:
            # Skip female voice on Oromo fallback to keep sample set clean
            if lang == "om" and "Female" in prov_label:
                continue

            clean_prov_name = prov_label.replace(" ", "_").replace("(", "").replace(")", "").lower()
            filename = f"{ans_id}_{lang}_{clean_prov_name}.wav"
            filepath = output_dir / filename

            # Synthesize 8 kHz mono linear PCM
            pcm_8k = await provider.synthesize(text, voice=voice, language=lang)
            if pcm_8k:
                wav_bytes = pcm8k_to_wav(pcm_8k)
                filepath.write_bytes(wav_bytes)
                print(f"  ✓ Rendered {filename} ({len(wav_bytes)} bytes)")
            else:
                print(f"  ✗ Failed {filename}")

            records.append({
                "Sample_ID": ans_id,
                "Language": lang,
                "Topic": ans["topic"],
                "Provider": prov_label,
                "Voice": voice,
                "Audio_File": f"eval/reports/tts_samples/{filename}",
                "Text": text,
                "Phone_Speaker_Intelligibility_1to5": "",
                "Cadence_Naturalness_1to5": "",
                "Reviewer_Notes": "",
            })

    # Write evaluation CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "Sample_ID", "Language", "Topic", "Provider", "Voice",
            "Audio_File", "Text", "Phone_Speaker_Intelligibility_1to5",
            "Cadence_Naturalness_1to5", "Reviewer_Notes"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print("-" * 80)
    print(f"Evaluation rating sheet generated: {csv_path}")
    print(f"All WAV samples stored in: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_comparison())
