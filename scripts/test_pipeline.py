import asyncio
import edge_tts
from app.audio.convert import audio_stream_to_pcm8k
from app.pipeline import SessionState, process_utterance

async def test_full_pipeline():
    print("=" * 60)
    print("TESTING FULL PIPELINE WITH GEMINI STT + RAG + LLM + TTS")
    print("=" * 60)

    # 1. Generate audio utterance simulating farmer asking in Amharic
    sample_text = "በቆሎ ላይ ተምች ወደቀብኝ ምን ላድርግ?"
    c = edge_tts.Communicate(sample_text, "am-ET-MekdesNeural")
    mp3 = b"".join([chunk["data"] async for chunk in c.stream() if chunk["type"] == "audio"])
    pcm8k = audio_stream_to_pcm8k(mp3)
    print(f"1. Spoken input audio generated: {len(pcm8k)} bytes ({len(pcm8k)/16000:.2f}s)")

    # 2. Run pipeline
    session = SessionState(session_id="test_call_001", caller_hash="test_hash")
    res = await process_utterance(
        audio_bytes=pcm8k,
        session=session,
        text_override=None,
        synthesize_audio=True
    )

    print("\n--- RESULTS ---")
    print("STT / Answer Gloss:", res.metadata.answer_en_gloss)
    print("AI Answer Text (Amharic):", res.text)
    print("Audio bytes synthesized:", len(res.audio) if res.audio else 0)
    print("Confidence:", res.metadata.confidence)
    print("Latency breakdown:", res.metadata.latency_ms)
    print("Sources used:", [s["title"] for s in res.metadata.sources_used])
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
