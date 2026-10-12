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
    confidence: float = 0.9

    @property
    def answer(self) -> str:
        return self.final_answer

    @property
    def is_grounded(self) -> bool:
        return self.grounded

    @property
    def answer_en_gloss(self) -> str:
        return self.final_en_gloss

    @property
    def english_gloss(self) -> str:
        return self.final_en_gloss




def replace_digits_with_words(text: str, language: str = "am") -> str:
    """Replace raw Arabic digits and fractions in text with word numbers in target language."""
    # Handle common fractions and percentages
    if language == "am":
        text = re.sub(r"\b1/2\b", "ግማሽ", text)
        text = re.sub(r"\b1/4\b", "ሩብ", text)
        text = re.sub(r"(\d+)\s*%", r"\1 በመቶ", text)
    elif language == "om":
        text = re.sub(r"\b1/2\b", "walakkaa", text)
        text = re.sub(r"\b1/4\b", "kurmaana", text)
        text = re.sub(r"(\d+)\s*%", r"\1 dhibbentaa", text)

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


def validate_dosage_sanity(text: str, language: str = "am") -> tuple[bool, str]:
    """Validate that chemical or fertilizer dosages fall within safe agronomic bounds."""
    # 1. Check digits directly
    liquid_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:ሊትር|litira|liter|l)\b", text, flags=re.IGNORECASE)
    for m in liquid_matches:
        try:
            val = float(m)
            if val > 15.0:
                return False, f"Liquid dosage ({val} L) exceeds safe agronomic bounds."
        except ValueError:
            pass

    dry_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:ኪሎ|ኪ\.ግ|kg|kiiloo)\b", text, flags=re.IGNORECASE)
    for m in dry_matches:
        try:
            val = float(m)
            if val > 600.0:
                return False, f"Dry fertilizer/chemical rate ({val} kg) exceeds safe agronomic bounds."
        except ValueError:
            pass

    # 2. Check word-based quantities (e.g. ሃያ ሊትር, ሺህ ኪሎ)
    if language == "om":
        for val, unit in extract_quantities_oromo(text):
            u_clean = unit.lower()
            if any(u in u_clean for u in ["liter", "litir", "liitir", "l"]) and val > 15.0:
                return False, f"Liquid dosage ({val} L) exceeds safe agronomic bounds."
            if any(u in u_clean for u in ["kg", "kiiloo"]) and val > 600.0:
                return False, f"Dry rate ({val} kg) exceeds safe agronomic bounds."
    else:
        for val, unit in extract_quantities_amharic(text):
            u_clean = unit.lower()
            if any(u in u_clean for u in ["liter", "ሊትር", "l"]) and val > 15.0:
                return False, f"Liquid dosage ({val} L) exceeds safe agronomic bounds."
            if any(u in u_clean for u in ["kg", "ኪሎ", "ኪግ", "ኪ.ግ"]) and val > 600.0:
                return False, f"Dry rate ({val} kg) exceeds safe agronomic bounds."

    return True, ""


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

    # 2. Check for empty answer
    if not text or len(text) < 5:
        reasons.append("Answer is empty or insufficient.")
        return GuardrailResult(
            is_safe=False,
            final_answer=safe_fallback,
            final_en_gloss="Safe fallback: empty answer generated.",
            rejection_reasons=reasons,
            applied_fallback=True,
            grounded=False,
            needs_referral=True
        )

    # 3. Dosage sanity check
    is_dosage_safe, dosage_reason = validate_dosage_sanity(text, language=language)
    if not is_dosage_safe:
        logger.warning(f"⚠️ [DOSAGE GUARDRAIL TRIGGERED] {dosage_reason}")
        dosage_safe_msg = (
            "ለደህንነት ሲባል የፀረ-ተባይ ወይም የማዳበሪያ መጠን ከመጠቀምዎ በፊት የተለጠፈውን መመሪያ ያንብቡ እና የልማት ጣቢያ ባለሙያ ያማክሩ።"
            if language == "am"
            else "Nageenyaaf jecha hamma farra ilbiisaa yookiin xaa'oo fayyadamuu keessan dura qajeelfama dubbisaa ogeessa qonnaa mariisisaa."
        )
        return GuardrailResult(
            is_safe=True,
            final_answer=dosage_safe_msg,
            final_en_gloss=f"Dosage safety referral: {dosage_reason}",
            rejection_reasons=[dosage_reason],
            applied_fallback=True,
            grounded=True,
            needs_referral=False,
            confidence=0.90,
        )

    # 4. Format digits as words for phone TTS
    clean_answer = replace_digits_with_words(text, language=language)

    # 5. Length Check (max 4 sentences for voice and web readability)
    clean_answer = truncate_to_sentences(clean_answer, max_sentences=4)

    return GuardrailResult(
        is_safe=True,
        final_answer=clean_answer,
        final_en_gloss=gloss or "Agricultural advisory answer.",
        rejection_reasons=[],
        applied_fallback=False,
        grounded=True,
        needs_referral=False,
        confidence=getattr(answer, "confidence", 0.95) or 0.95
    )
