import asyncio
import io
import wave
import httpx
from app.config import settings
from app.audio.convert import audio_stream_to_pcm8k, pcm8k_to_pcm16k
import edge_tts

async def run():
    text_in = "በቆሎ ላይ ተምች ወደቀብኝ ምን ላድርግ?"
    c = edge_tts.Communicate(text_in, "am-ET-AmehaNeural")
    mp3_data = b"".join([chunk["data"] async for chunk in c.stream() if chunk["type"] == "audio"])
    pcm8k = audio_stream_to_pcm8k(mp3_data)
    pcm16k = pcm8k_to_pcm16k(pcm8k)
    
    buf16k = io.BytesIO()
    with wave.open(buf16k, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm16k)
    wav16k = buf16k.getvalue()

    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test A: Whisper with english prompt hint
        r = await client.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers=headers,
            files={"file": ("speech.wav", wav16k, "audio/wav")},
            data={"model": "whisper-large-v3", "prompt": "Ethiopian farmer asking in Amharic: በቆሎ፣ ጤፍ፣ ስንዴ"}
        )
        t = r.json().get("text", "")
        print("Whisper output:", t)

        # Send to Qwen to interpret the farmer's question
        chat_payload = {
            "model": "qwen/qwen3.8-27b",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an Ethiopian agricultural assistant. A farmer spoke an agricultural question in Amharic. "
                        "Because of telephony audio, the speech-to-text transcript might be slightly phonetic or noisy. "
                        "Identify what agricultural problem or question they are asking. "
                        "Provide a clear, helpful agricultural answer in Amharic."
                    )
                },
                {"role": "user", "content": f"Farmer transcript: {t}"}
            ],
            "temperature": 0.1
        }
        r2 = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=chat_payload)
        print("Qwen Answer:", r2.json()["choices"][0]["message"]["content"])

if __name__ == "__main__":
    asyncio.run(run())
