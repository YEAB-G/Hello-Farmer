import os
import sys
import time
import httpx
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

try:
    from backend.app.config import settings
except ImportError:
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
    async with httpx.AsyncClient(timeout=15.0) as client:
        t0 = time.time()
        r1 = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=p1)
        dur1 = time.time() - t0
        print(f"P1 (JSON mode): status={r1.status_code}, latency={dur1:4.2f}s, response={r1.text[:120]}")

        t1 = time.time()
        r2 = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=p2)
        dur2 = time.time() - t1
        print(f"P2 (Standard): status={r2.status_code}, latency={dur2:4.2f}s, response={r2.text[:120]}")


if __name__ == "__main__":
    asyncio.run(test())

