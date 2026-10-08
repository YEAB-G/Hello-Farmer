"""Local Ollama LLM fallback provider.

WARNING: Per Section 4 of system prompt, local models in Ollama exhibit
substantially lower translation, script rendering, and agronomic reasoning
quality for Amharic and Afaan Oromo compared to frontier cloud models.
"""
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


class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama fallback provider."""

    def __init__(self, base_url: str | None = None, model: str = "qwen2.5:7b"):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model

    async def generate_response(
        self,
        transcript: str,
        retrieved_passages: list[dict[str, Any]],
        conversation_history: list[dict[str, str]],
        farmer_context: dict[str, Any],
        weather_info: dict[str, Any] | None = None,
        language: str = "am"
    ) -> LLMAnswer:
        logger.warning(
            "Using local Ollama fallback for language '%s'. "
            "Quality for Amharic/Oromo is substantially degraded compared to Gemini.",
            language
        )

        system_msg = build_system_prompt(language)
        user_msg = format_user_prompt(
            transcript=transcript,
            retrieved_passages=retrieved_passages,
            conversation_history=conversation_history,
            farmer_context=farmer_context,
            weather_info=weather_info,
            language=language
        )

        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2}
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["message"]["content"]
            parsed = json.loads(content)
            return LLMAnswer(
                answer=parsed.get("answer", "").strip(),
                answer_en_gloss=parsed.get("answer_en_gloss", "").strip(),
                grounded=bool(parsed.get("grounded", False)),
                sources_used=parsed.get("sources_used", []),
                needs_referral=bool(parsed.get("needs_referral", False)),
                topic=parsed.get("topic", "general"),
                confidence=float(parsed.get("confidence", 0.6))
            )
