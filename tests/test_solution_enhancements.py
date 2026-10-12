"""Unit tests for AI Solution-Finding enhancements:
1. 3-Step Agronomic Prescription Prompting
2. Multi-Turn Query Reformulation
3. Live Weather-Integrated Advisory
4. Semantic FAQ Cache
5. Dosage Sanity & Number Guardian
"""
import pytest
from backend.app.pipeline import SessionState, reformulate_search_query
from backend.app.rag.faq_cache import match_agricultural_faq
from backend.app.safety.guardrails import (
    replace_digits_with_words,
    validate_dosage_sanity,
)


def test_faq_cache_instant_match_amharic():
    """Verify high-frequency teff fertilizer question matches FAQ cache."""
    query = "ጤፍ ላይ ማዳበሪያ ዩሪያ መጠን ስንት ነው?"
    match = match_agricultural_faq(query, language="am")

    assert match is not None
    assert "መቶ ኪሎ ግራም" in match.answer
    assert "ኤን ፒ ኤስ" in match.answer
    assert match.confidence >= 0.95


def test_faq_cache_instant_match_oromo():
    """Verify high-frequency Oromo wheat rust question matches FAQ cache."""
    query = "qamadii waagii keelloo akkamitti ittisuu danda'ama?"
    match = match_agricultural_faq(query, language="om")

    assert match is not None
    assert "waagii qamadii" in match.answer
    assert match.confidence >= 0.95


def test_query_reformulation_enriches_followup():
    """Verify short follow-up query is enriched with session crop and symptom context."""
    session = SessionState(session_id="test_session", caller_hash="hash_test_123")
    session.extracted_crop = "ስንዴ"
    session.extracted_symptoms = "ቢጫ ዝገት"

    # Farmer asks short ambiguous follow-up
    raw_followup = "መድሃኒቱ በስንት ቀን ልዩነት ይረጫል?"
    enriched = reformulate_search_query(raw_followup, session)

    assert "ስንዴ" in enriched
    assert "ቢጫ ዝገት" in enriched
    assert "በስንት ቀን" in enriched


def test_dosage_sanity_allows_normal_rates():
    """Verify standard extension dosages pass sanity check."""
    normal_text = "በአንድ ሄክታር አንድ ሊትር ፀረ-ፈንገስ መድኃኒት እና መቶ ኪሎ ግራም ዩሪያ ይረጩ።"
    is_safe, _ = validate_dosage_sanity(normal_text)
    assert is_safe is True


def test_dosage_sanity_flags_excessive_rates():
    """Verify dangerously high chemical or fertilizer dosages trigger safety alert."""
    excessive_text = "በአንድ ሄክታር ሃያ ሊትር ፀረ-ተባይ መድኃኒት ይርጩ።"
    is_safe, reason = validate_dosage_sanity(excessive_text)
    assert is_safe is False
    assert "exceeds safe agronomic bounds" in reason


def test_number_guardian_converts_digits_and_fractions():
    """Verify Number Guardian converts fractions, percentages, and Arabic digits into words."""
    # Amharic
    am_text = "በ 1 ሄክታር 1/2 ሊትር እና 100 kg ማዳበሪያ በ 8028 ይደውሉ።"
    am_words = replace_digits_with_words(am_text, language="am")
    assert "1/2" not in am_words
    assert "ግማሽ" in am_words
    assert "100" not in am_words
    assert "መቶ" in am_words

    # Afaan Oromo
    om_text = "Hektaara 1 keessatti 1/2 liitira fi 100 kg xaa'oo fayyadamaa."
    om_words = replace_digits_with_words(om_text, language="om")
    assert "1/2" not in om_words
    assert "walakkaa" in om_words
    assert "100" not in om_words
    assert "dhibba" in om_words
