"""Unit tests for Phase 4: LLM prompts, guardrails, fallback chain, and safety."""
import pytest
from backend.app.llm.base import LLMAnswer
from backend.app.llm.chain import LLMFallbackChain
from backend.app.llm.prompts import build_system_prompt, format_user_prompt
from backend.app.safety.guardrails import (
    replace_digits_with_words,
    truncate_to_sentences,
    validate_and_guard,
)


def test_prompts_structure_and_formatting():
    """Verify system prompt enforces sentence limits, spoken style, and JSON schema."""
    sys_am = build_system_prompt("am")
    assert "WRITE ALL NUMBERS AS WORDS" in sys_am
    assert "At most 3 short sentences" in sys_am
    assert "NEVER invent or guess pesticide names" in sys_am

    sys_om = build_system_prompt("om")
    assert "Afaan Oromo" in sys_om

    user_prompt = format_user_prompt(
        transcript="የስንዴ በሽታ",
        retrieved_passages=[{"chunk_id": "c_1", "title": "Wheat Doc", "source_tier": "tier_1", "text": "ምልክት"}],
        conversation_history=[],
        farmer_context={"crop": "ስንዴ", "location": "አርሲ"},
        language="am"
    )
    assert "Crop: ስንዴ" in user_prompt
    assert "Location: አርሲ" in user_prompt
    assert "Wheat Doc" in user_prompt


def test_guardrail_replaces_arabic_digits():
    """Verify Arabic digits in speech answers are converted to spoken words."""
    text_am = "በማሳው ላይ 2 ሄክታር መሬት አለኝ። 5 ኪሎ ዘር ያስፈልጋል።"
    converted_am = replace_digits_with_words(text_am, language="am")
    assert "2" not in converted_am
    assert "5" not in converted_am
    assert "ሁለት" in converted_am
    assert "አምስት" in converted_am

    text_om = "Lafa hektaara 3 qabna."
    converted_om = replace_digits_with_words(text_om, language="om")
    assert "3" not in converted_om
    assert "sadii" in converted_om


def test_guardrail_truncates_long_answers():
    """Verify answer length is capped at maximum 3 sentences."""
    long_answer = "ይህ አንደኛ ዓረፍተ ነገር ነው። ይህ ሁለተኛ ዓረፍተ ነገር ነው። ይህ ሦስተኛ ዓረፍተ ነገር ነው። ይህ አራተኛ ዓረፍተ ነገር ነው። ይህ አምስተኛ ዓረፍተ ነገር ነው።"
    truncated = truncate_to_sentences(long_answer, max_sentences=3)
    sentences = [s for s in truncated.split("።") if s.strip()]
    assert len(sentences) == 3


def test_guardrail_detects_hallucinated_quantities():
    """Verify hallucinated numbers not present in retrieved context trigger safe fallback."""
    answer = LLMAnswer(
        answer="በአንድ ሄክታር ሃምሳ ኩንታል ምርት ማግኘት ይቻላል።",
        answer_en_gloss="Fifty quintals per hectare.",
        grounded=True,
        sources_used=[],
        needs_referral=False,
        topic="yield"
    )
    # Context only mentions 20 quintals, NOT 50
    context = [{"text": "የጤፍ ምርት በአንድ ሄክታር ሃያ ኩንታል ሊደርስ ይችላል።", "source_tier": "tier_1"}]

    res = validate_and_guard(answer, context, language="am")
    assert res.is_safe is False
    assert res.applied_fallback is True
    assert res.needs_referral is True
    assert "Hallucinated numeric quantities" in res.rejection_reasons[0]


def test_guardrail_chemical_dose_on_placeholder_rejected():
    """Verify chemical recommendations without Tier 1 sources are blocked."""
    answer = LLMAnswer(
        answer="ለዚህ በሽታ ሁለት ሊትር ኬሚካል በሄክታር መርጨት ይችላሉ።",
        answer_en_gloss="Spray two liters chemical.",
        grounded=True,
        sources_used=[],
        needs_referral=False,
        topic="chemical"
    )
    # Context is placeholder tier
    context = [{"text": "የሰብል በሽታ አጠቃላይ መረጃ።", "source_tier": "placeholder"}]

    res = validate_and_guard(answer, context, language="am", caller_question="ኬሚካል ልርጭ?")
    assert res.is_safe is False
    assert res.applied_fallback is True
    assert "does not allow chemical/dosage recommendations" in res.rejection_reasons[0]


def test_guardrail_emergency_referral():
    """Verify acute poisoning or medical emergency triggers immediate referral."""
    answer = LLMAnswer(
        answer="የተለመደ መረጃ።",
        answer_en_gloss="Generic info.",
        grounded=True,
        sources_used=[],
        needs_referral=False,
        topic="emergency"
    )
    context = [{"text": "መረጃ", "source_tier": "tier_1"}]

    res_am = validate_and_guard(answer, context, language="am", caller_question="ልጄ ፀረ-ተባይ ጠጥቷል መመረዝ አጋጥሞታል")
    assert "የጤና ጣቢያ" in res_am.final_answer or "ሐኪም" in res_am.final_answer
    assert res_am.needs_referral is True

    res_om = validate_and_guard(answer, context, language="om", caller_question="namni summii dhugeera")
    assert "buufata fayyaa" in res_om.final_answer
    assert res_om.needs_referral is True


@pytest.mark.asyncio
async def test_llm_fallback_chain_offline():
    """Verify fallback chain safely catches missing cloud keys and provides spoken safe fallback."""
    chain = LLMFallbackChain()
    # Force empty context and unconfigured keys
    answer = await chain.generate_response(
        transcript="ሰላም",
        retrieved_passages=[],
        conversation_history=[],
        farmer_context={},
        language="am"
    )
    assert answer is not None
    assert answer.needs_referral is True
    assert "ስምንት ዜሮ ሁለት ስምንት" in answer.answer
