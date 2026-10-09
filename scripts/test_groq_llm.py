import httpx
import asyncio
from app.config import settings

async def test():
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
    p1 = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": "respond with a valid json object with key answer"}],
        "response_format": {"type": "json_object"}
    }
    p2 = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "user", "content": "respond with a valid json object with key answer"}]
    }
    async with httpx.AsyncClient() as client:
        r1 = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=p1)
        print("P1 status:", r1.status_code, r1.text[:120])
        r2 = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=p2)
        print("P2 status:", r2.status_code, r2.text[:120])

if __name__ == "__main__":
    asyncio.run(test())
