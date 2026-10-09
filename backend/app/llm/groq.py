"""Groq LLM fallback provider using OpenAI-compatible HTTP endpoint."""
import json
import logging
from typing import Any

import httpx
from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider, LLMAnswer
from backend.app.llm.prompts import (
    build_system_prompt,
    format_user_prompt,
)

logger = logging.getLogger(__name__)


class GroqLLMProvider(BaseLLMProvider):
    """Groq API fallback provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate_response(
        self,
        transcript: str,
        retrieved_passages: list[dict[str, Any]],
        conversation_history: list[dict[str, str]],
        farmer_context: dict[str, Any],
        weather_info: dict[str, Any] | None = None,
        language: str = "am"
    ) -> LLMAnswer:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not configured.")

        system_msg = build_system_prompt(language)
        user_msg = format_user_prompt(
            transcript=transcript,
            retrieved_passages=retrieved_passages,
            conversation_history=conversation_history,
            farmer_context=farmer_context,
            weather_info=weather_info,
            language=language
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(self.base_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            parsed = json.loads(content.strip())
            return LLMAnswer(
                answer=parsed.get("answer", "").strip(),
                answer_en_gloss=parsed.get("answer_en_gloss", "").strip(),
                grounded=bool(parsed.get("grounded", False)),
                sources_used=parsed.get("sources_used", []),
                needs_referral=bool(parsed.get("needs_referral", False)),
                topic=parsed.get("topic", "general"),
                confidence=float(parsed.get("confidence", 0.9))
            )
