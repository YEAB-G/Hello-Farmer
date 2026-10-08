"""Abstract interface for LLM providers."""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMAnswer(BaseModel):
    answer: str
    answer_en_gloss: str
    grounded: bool
    sources_used: list[dict[str, Any]] = Field(default_factory=list)
    needs_referral: bool = False
    topic: str | None = None
    confidence: float = 1.0


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_response(
        self,
        transcript: str,
        retrieved_passages: list[dict[str, Any]],
        conversation_history: list[dict[str, str]],
        farmer_context: dict[str, Any],
        weather_info: dict[str, Any] | None = None,
        language: str = "am"
    ) -> LLMAnswer:
        """Generate grounded, safe answer obeying all agricultural system prompt rules."""
