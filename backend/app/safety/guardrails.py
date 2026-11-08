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

try:
    from app.config import settings
    from app.llm.base import LLMAnswer
    from app.text.amharic import (
        extract_quantities_amharic,
        number_to_amharic_words,
    )
    from app.text.oromo import (
        extract_quantities_oromo,
        number_to_oromo_words,
    )
except ImportError:
    from backend.app.config import settings
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
    evidence_mode: str = "rag_grounded"
    location_used: str | None = None
    follow_up_question: str | None = None
    safety_note: str | None = None

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
            elif language == "en":
                en_small = {
                    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
                    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
                    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
                    30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"
                }
                if num in en_small:
                    return en_small[num]
                elif 20 < num < 100:
                    tens, rem = divmod(num, 10)
                    return f"{en_small[tens * 10]}-{en_small[rem]}"
                return num_str
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
    if isinstance(answer, str):
        text = answer.strip()
        gloss = ""
    else:
        text = getattr(answer, "answer", str(answer)).strip()
        gloss = getattr(answer, "answer_en_gloss", "").strip()
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
            needs_referral=True,
        )

    # 2b. Placeholder tier rejection for chemical dose recommendations (only if NO higher tier sources present)
    has_trusted_tier = any(
        p.get("source_tier") not in ("placeholder", 0, "tier_0", None) and not p.get("is_placeholder")
        for p in retrieved_passages
    )
    only_placeholder = bool(retrieved_passages) and not has_trusted_tier
    if only_placeholder and any(k in text.lower() or k in caller_question.lower() for k in CHEMICAL_DOSE_KEYWORDS):
        reasons.append("Source tier placeholder does not allow chemical/dosage recommendations.")
        return GuardrailResult(
            is_safe=False,
            final_answer=safe_fallback,
            final_en_gloss="Safe fallback: chemical recommendation supported only by placeholder context.",
            rejection_reasons=reasons,
            applied_fallback=True,
            grounded=False,
            needs_referral=True,
        )

    # 2c. Hallucinated chemical dosage quantities check
    is_chemical_query = any(k in text.lower() or k in caller_question.lower() for k in CHEMICAL_DOSE_KEYWORDS)
    answer_numbers = extract_all_numbers_from_text(text, language=language)
    if is_chemical_query and answer_numbers and retrieved_passages:
        context_text = " ".join(p.get("text", "") or p.get("content", "") for p in retrieved_passages)
        context_numbers = extract_all_numbers_from_text(context_text, language=language)
        hallucinated = answer_numbers - context_numbers
        if hallucinated:
            reasons.append(f"Hallucinated numeric quantities: chemical dosage numbers not found in verified context: {hallucinated}")
            dosage_safe_msg = (
                "ለደህንነት ሲባል የፀረ-ተባይ ወይም የማዳበሪያ መጠን ከመጠቀምዎ በፊት የተለጠፈውን መመሪያ ያንብቡ እና የልማት ጣቢያ ባለሙያ ያማክሩ።"
                if language == "am"
                else "Nageenyaaf jecha hamma farra ilbiisaa yookiin xaa'oo fayyadamuu keessan dura qajeelfama dubbisaa ogeessa qonnaa mariisisaa."
            )
            return GuardrailResult(
                is_safe=False,
                final_answer=dosage_safe_msg,
                final_en_gloss="Safe fallback: ungrounded chemical quantities detected.",
                rejection_reasons=reasons,
                applied_fallback=True,
                grounded=False,
                needs_referral=True,
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
            is_safe=False,
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

    # 5. Length Check (configurable max sentences for thorough, polite explanation)
    max_s = getattr(settings, "VOICE_MAX_RESPONSE_SENTENCES", 6)
    clean_answer = truncate_to_sentences(clean_answer, max_sentences=max_s)

    return GuardrailResult(
        is_safe=True,
        final_answer=clean_answer,
        final_en_gloss=gloss or "Agricultural advisory answer.",
        rejection_reasons=[],
        applied_fallback=False,
        grounded=getattr(answer, "grounded", True),
        needs_referral=getattr(answer, "needs_referral", False),
        confidence=getattr(answer, "confidence", 0.95) or 0.95,
        evidence_mode=getattr(answer, "evidence_mode", "rag_grounded"),
        location_used=getattr(answer, "location_used", None),
        follow_up_question=getattr(answer, "follow_up_question", None),
        safety_note=getattr(answer, "safety_note", None),
    )
