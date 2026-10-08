"""Safety guardrails for Hello Farmer voice assistant.

Enforces Section 6.4 and 6.6 rules:
- Grounding verification: rejection if quantities or chemical names appear without context.
- Numeric quantity check: every quantity in answer must appear in retrieved passages.
- Source tier check: chemical/dosage recommendations strictly prohibited from placeholder (Tier 0) or Tier 3/4.
- Digits check: conversion or rejection of raw Arabic digits in spoken answers.
- Length check: max 3 sentences (~40 words).
- Safe fallback with spoken referral to local DA or 8028 hotline.
"""
import logging
import re
from typing import Any

from backend.app.llm.base import LLMAnswer
from backend.app.text.amharic import (
    extract_quantities_amharic,
    number_to_amharic_words,
)
from backend.app.text.oromo import (
    extract_quantities_oromo,
    number_to_oromo_words,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

SAFE_FALLBACK_TEXTS = {
    "am": "ይቅርታ፣ ለዚህ ጥያቄ በቂ የተረጋገጠ መረጃ አላገኘሁም። እባክዎ የአካባቢዎን የግብርና ልማት ጣቢያ ባለሙያ ያማክሩ ወይም በስምንት ዜሮ ሁለት ስምንት ይደውሉ።",
    "om": "Dhiifama, gaaffii kanaaf ragaan amansiisaan gahaan hin jiru. Maaloo ogeessa misooma qonnaa naannoo keessanii gaafadhaa yookiin bilbila saddeet-duwwaa-lama-saddeet irratti bilbilaa.",
}

EMERGENCY_KEYWORDS = [
    "መመረዝ", "መርዝ", "ጠጥቷል", "summii", "dhuge", "poison", "emergency", "ሆስፒታል"
]

CHEMICAL_DOSE_KEYWORDS = [
    "ኪሚካል", "ኬሚካል", "መድሃኒት", "መርጨት", "መጠን", "ሊትር", "ግራም", "ኩንታል",
    "dawaa", "biifuu", "farra", "hamma", "litira", "graama", "dose", "chemical"
]


class GuardrailResult(BaseModel):
    is_safe: bool
    final_answer: str
    final_en_gloss: str
    rejection_reasons: list[str]
    applied_fallback: bool
    grounded: bool
    needs_referral: bool


def replace_digits_with_words(text: str, language: str = "am") -> str:
    """Replace raw Arabic digits in text with word numbers in target language."""
    def _rep(match):
        num_str = match.group(0)
        try:
            num = int(num_str)
            if language == "om":
                return number_to_oromo_words(num)
            return number_to_amharic_words(num)
        except Exception:
            return num_str

    return re.sub(r"\b\d+\b", _rep, text)


def truncate_to_sentences(text: str, max_sentences: int = 3) -> str:
    """Ensure answer is at most max_sentences sentences long."""
    # Split on Ethiopic full stop (፧ / ።) or Latin punctuation (. / ! / ?)
    sentences = re.split(r"(?<=[።.!?])\s+", text.strip())
    if len(sentences) > max_sentences:
        logger.info(f"Guardrail truncated answer from {len(sentences)} to {max_sentences} sentences.")
        return " ".join(sentences[:max_sentences])
    return text


def extract_all_numbers_from_text(text: str, language: str = "am") -> set[float]:
    """Extract all numeric quantities (digits or words) from text."""
    numbers: set[float] = set()

    # 1. Direct digits
    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        try:
            numbers.add(float(m.group(0)))
        except ValueError:
            pass

    # 2. Language-specific quantity extractors
    if language == "om":
        for val, _ in extract_quantities_oromo(text):
            numbers.add(val)
    else:
        for val, _ in extract_quantities_amharic(text):
            numbers.add(val)

    return numbers


def validate_and_guard(
    answer: LLMAnswer,
    retrieved_passages: list[dict[str, Any]],
    language: str = "am",
    caller_question: str = ""
) -> GuardrailResult:
    """Validate LLM answer against all safety guardrails.

    Returns GuardrailResult with final safe spoken answer.
    """
    reasons: list[str] = []
    text = answer.answer.strip()
    gloss = answer.answer_en_gloss.strip()
    safe_fallback = SAFE_FALLBACK_TEXTS.get(language, SAFE_FALLBACK_TEXTS["am"])

    # 1. Emergency detection check
    is_emergency = any(k in caller_question.lower() or k in text.lower() for k in EMERGENCY_KEYWORDS)
    if is_emergency:
        emergency_msg = (
            "አስቸኳይ የጤና ወይም የእንስሳት ህክምና አደጋ ካለ በአስቸኳይ በአቅራቢያዎ ወደሚገኝ የጤና ጣቢያ ወይም ሐኪም ዘንድ ይሂዱ።"
            if language == "am"
            else "Yoo balaan fayyaa yookiin beeyladaa tasaa mudate, battalumatti gara buufata fayyaa yookiin ogeessaatti fiigaa."
        )
        return GuardrailResult(
            is_safe=True,
            final_answer=emergency_msg,
            final_en_gloss="Emergency alert: seek immediate medical or veterinary care.",
            rejection_reasons=["Emergency medical/veterinary referral triggered"],
            applied_fallback=True,
            grounded=True,
            needs_referral=True
        )

    # 2. Check if answer needs referral or is ungrounded
    if answer.needs_referral or not answer.grounded:
        reasons.append("Answer marked as ungrounded or requesting referral by LLM.")
        return GuardrailResult(
            is_safe=False,
            final_answer=safe_fallback,
            final_en_gloss="Safe fallback: ungrounded or insufficient data.",
            rejection_reasons=reasons,
            applied_fallback=True,
            grounded=False,
            needs_referral=True
        )

    # 3. Check for empty passages
    if not retrieved_passages:
        reasons.append("No retrieved passages available to ground the answer.")
        return GuardrailResult(
            is_safe=False,
            final_answer=safe_fallback,
            final_en_gloss="Safe fallback: zero passages retrieved.",
            rejection_reasons=reasons,
            applied_fallback=True,
            grounded=False,
            needs_referral=True
        )

    # Aggregate context text and highest source tier
    context_text = " ".join(p.get("text", "") for p in retrieved_passages)
    highest_tier = "placeholder"
    for p in retrieved_passages:
        tier = p.get("source_tier", "placeholder")
        if tier in ("tier_1", 1):
            highest_tier = "tier_1"
            break
        elif tier in ("tier_2", 2) and highest_tier != "tier_1":
            highest_tier = "tier_2"

    # 4. Source Tier & Chemical/Dosage Gate (Section 6.4)
    mentions_chemicals_or_dose = any(k in text.lower() or k in caller_question.lower() for k in CHEMICAL_DOSE_KEYWORDS)
    if mentions_chemicals_or_dose and highest_tier not in ("tier_1", "tier_2"):
        reasons.append(
            f"Chemical or dosage topic detected, but source tier '{highest_tier}' does not allow chemical/dosage recommendations."
        )
        return GuardrailResult(
            is_safe=False,
            final_answer=safe_fallback,
            final_en_gloss="Safe fallback: chemical/dose recommendations prohibited on placeholder/unvetted tiers.",
            rejection_reasons=reasons,
            applied_fallback=True,
            grounded=False,
            needs_referral=True
        )

    # 5. Numeric Grounding Check (Section 6.6)
    # Every numeric quantity in answer must appear in retrieved context
    answer_numbers = extract_all_numbers_from_text(text, language=language)
    context_numbers = extract_all_numbers_from_text(context_text, language=language)

    hallucinated_numbers = []
    for num in answer_numbers:
        # Check if num is close to any context number
        if not any(abs(num - c_num) < 0.05 for c_num in context_numbers):
            hallucinated_numbers.append(num)

    if hallucinated_numbers:
        reasons.append(
            f"Hallucinated numeric quantities detected in answer: {hallucinated_numbers}. Not found in context: {context_numbers}"
        )
        return GuardrailResult(
            is_safe=False,
            final_answer=safe_fallback,
            final_en_gloss=f"Safe fallback: ungrounded numeric values {hallucinated_numbers}.",
            rejection_reasons=reasons,
            applied_fallback=True,
            grounded=False,
            needs_referral=True
        )

    # 6. Format digits as words for phone TTS
    clean_answer = replace_digits_with_words(text, language=language)

    # 7. Length Check (max 3 sentences)
    clean_answer = truncate_to_sentences(clean_answer, max_sentences=3)

    return GuardrailResult(
        is_safe=True,
        final_answer=clean_answer,
        final_en_gloss=gloss,
        rejection_reasons=[],
        applied_fallback=False,
        grounded=True,
        needs_referral=False
    )
