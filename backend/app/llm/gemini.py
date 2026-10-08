"""Google Gemini LLM provider for Hello Farmer.

Primary LLM engine using Google Gemini API (gemini-2.5-flash / gemini-1.5-flash)
with JSON structured schema output, 8-second timeout, and repair retry.
"""
import asyncio
import json
import logging
from typing import Any

from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider, LLMAnswer
from backend.app.llm.prompts import (
    REPAIR_PROMPT,
    build_system_prompt,
    format_user_prompt,
)

logger = logging.getLogger(__name__)


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM provider generating structured agronomic answers."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL or "gemini-2.5-flash"
        self._client = None
        self._initialized = False

    def _init_client(self):
        if not self._initialized:
            if not self.api_key:
                logger.warning("GEMINI_API_KEY not configured. Gemini provider will not execute live queries.")
            else:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    self._client = genai.GenerativeModel(
                        model_name=self.model_name,
                        generation_config={
                            "response_mime_type": "application/json",
                            "temperature": 0.2,
                        }
                    )
                    self._initialized = True
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini client: {e}")

    async def generate_response(
        self,
        transcript: str,
        retrieved_passages: list[dict[str, Any]],
        conversation_history: list[dict[str, str]],
        farmer_context: dict[str, Any],
        weather_info: dict[str, Any] | None = None,
        language: str = "am"
    ) -> LLMAnswer:
        """Call Gemini Flash with system prompt, passages, and 8s timeout."""
        self._init_client()
        if not self._client:
            raise RuntimeError("Gemini client is not initialized or API key is missing.")

        system_instruction = build_system_prompt(language)
        user_prompt = format_user_prompt(
            transcript=transcript,
            retrieved_passages=retrieved_passages,
            conversation_history=conversation_history,
            farmer_context=farmer_context,
            weather_info=weather_info,
            language=language
        )

        full_prompt = f"{system_instruction}\n\n{user_prompt}"

        # Attempt 1 with 8.0s timeout
        try:
            raw_text = await asyncio.wait_for(
                self._async_generate(full_prompt),
                timeout=8.0
            )
            return self._parse_json_response(raw_text)
        except (asyncio.TimeoutError, json.JSONDecodeError, ValueError) as err:
            logger.warning(f"Gemini attempt 1 failed ({err}), retrying once with repair prompt...")

        # Attempt 2 (Repair prompt) with 8.0s timeout
        repair_full = f"{full_prompt}\n\n{REPAIR_PROMPT}"
        raw_text_retry = await asyncio.wait_for(
            self._async_generate(repair_full),
            timeout=8.0
        )
        return self._parse_json_response(raw_text_retry)

    async def _async_generate(self, prompt: str) -> str:
        """Run blocking Gemini SDK call in default asyncio thread executor."""
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.generate_content(prompt)
        )
        return response.text

    def _parse_json_response(self, text: str) -> LLMAnswer:
        """Parse and validate JSON response into pydantic LLMAnswer."""
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        data = json.loads(clean_text)
        return LLMAnswer(
            answer=data.get("answer", "").strip(),
            answer_en_gloss=data.get("answer_en_gloss", "").strip(),
            grounded=bool(data.get("grounded", False)),
            sources_used=data.get("sources_used", []),
            needs_referral=bool(data.get("needs_referral", False)),
            topic=data.get("topic", "general"),
            confidence=float(data.get("confidence", 1.0))
        )
