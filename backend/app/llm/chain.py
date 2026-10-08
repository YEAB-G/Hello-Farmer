"""LLM Fallback Chain.

Orchestrates primary LLM call through configured provider and executes graceful failover:
Primary (Gemini) -> Groq -> OpenRouter -> Ollama -> Spoken Safe Fallback.
"""
import logging
from typing import Any

from backend.app.config import settings
from backend.app.llm.base import BaseLLMProvider, LLMAnswer
from backend.app.llm.gemini import GeminiLLMProvider
from backend.app.llm.groq import GroqLLMProvider
from backend.app.llm.ollama import OllamaLLMProvider
from backend.app.llm.openrouter import OpenRouterLLMProvider

logger = logging.getLogger(__name__)

SAFE_FALLBACK_TEXTS = {
    "am": "ይቅርታ፣ ለዚህ ጥያቄ በቂ የተረጋገጠ መረጃ አላገኘሁም። እባክዎ የአካባቢዎን የግብርና ልማት ጣቢያ ባለሙያ ያማክሩ ወይም በስምንት ዜሮ ሁለት ስምንት ይደውሉ።",
    "om": "Dhiifama, gaaffii kanaaf ragaan amansiisaan gahaan hin jiru. Maaloo ogeessa misooma qonnaa naannoo keessanii gaafadhaa yookiin bilbila saddeet-duwwaa-lama-saddeet irratti bilbilaa.",
}


class LLMFallbackChain(BaseLLMProvider):
    """Executes provider chain with automatic fallback to safe referral."""

    def __init__(self):
        self.gemini = GeminiLLMProvider()
        self.groq = GroqLLMProvider()
        self.openrouter = OpenRouterLLMProvider()
        self.ollama = OllamaLLMProvider()

    async def generate_response(
        self,
        transcript: str,
        retrieved_passages: list[dict[str, Any]],
        conversation_history: list[dict[str, str]],
        farmer_context: dict[str, Any],
        weather_info: dict[str, Any] | None = None,
        language: str = "am"
    ) -> LLMAnswer:
        providers = [
            ("gemini", self.gemini),
            ("groq", self.groq),
            ("openrouter", self.openrouter),
            ("ollama", self.ollama),
        ]

        # Prioritize configured provider if different
        primary_name = settings.LLM_PROVIDER.lower()
        ordered = [p for p in providers if p[0] == primary_name] + [
            p for p in providers if p[0] != primary_name
        ]

        errors = []
        for name, provider in ordered:
            try:
                answer = await provider.generate_response(
                    transcript=transcript,
                    retrieved_passages=retrieved_passages,
                    conversation_history=conversation_history,
                    farmer_context=farmer_context,
                    weather_info=weather_info,
                    language=language
                )
                logger.info("Successfully generated answer via LLM provider '%s'", name)
                return answer
            except Exception as e:
                logger.warning("LLM provider '%s' failed: %s. Proceeding to fallback...", name, e)
                errors.append(f"{name}: {e}")

        # Terminal Safe Fallback
        logger.error("All LLM providers in fallback chain failed: %s. Using safe fallback.", errors)
        fallback_msg = SAFE_FALLBACK_TEXTS.get(language, SAFE_FALLBACK_TEXTS["am"])
        return LLMAnswer(
            answer=fallback_msg,
            answer_en_gloss="Safe fallback: insufficient verified data, referring to DA or 8028 hotline.",
            grounded=False,
            sources_used=[],
            needs_referral=True,
            topic="general",
            confidence=0.0
        )
