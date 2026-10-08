"""Unit tests for Phase 9: Afaan Oromo End-to-End integration and language resolution."""
import pytest

from app.language.detect import detect_text_language, format_language_switch_confirmation
from app.pipeline import SessionState, process_utterance
from app.safety.guardrails import replace_digits_with_words
from app.sms.summary import generate_post_call_sms_summary


def test_oromo_language_detection_heuristics():
    """Verify Afaan Oromo detection from text scripts and phrases."""
    # Common agricultural query in Afaan Oromo
    text_om = "Boqqoolloo irratti dhibeen baalaa keelloo ta'eera maaltu furmaata?"
    lang, conf = detect_text_language(text_om)
    assert lang == "om"
    assert conf >= 0.85

    # Greeting / choice in Afaan Oromo
    text_greet = "Akkam, Afaan Oromoo dubbachuu barbaada."
    lang2, conf2 = detect_text_language(text_greet)
    assert lang2 == "om"
    assert conf2 >= 0.90

    # Amharic query must be detected as 'am'
    text_am = "የጤፍ ሰብል ላይ ቢጫ ቅጠል ታይቷል"
    lang_am, conf_am = detect_text_language(text_am)
    assert lang_am == "am"
    assert conf_am >= 0.95


def test_oromo_digit_transliteration_to_words():
    """Verify numeric digits in Afaan Oromo are transliterated to words for phone speech."""
    raw_text = "Lafa hektaara 2 irratti qoricha liitira 5 biifna."
    spoken_text = replace_digits_with_words(raw_text, language="om")
    assert "2" not in spoken_text
    assert "5" not in spoken_text
    assert "lama" in spoken_text
    assert "shan" in spoken_text


def test_language_switch_confirmation_phrasing():
    """Verify spoken language switch confirmation phrasing."""
    confirm_om = format_language_switch_confirmation("om")
    assert "Afaan Oromootti" in confirm_om
    assert "gaaffii" in confirm_om

    confirm_am = format_language_switch_confirmation("am")
    assert "አማርኛ" in confirm_am


@pytest.mark.asyncio
async def test_oromo_weather_query():
    """Verify pipeline handles weather questions in Afaan Oromo."""
    session = SessionState(
        session_id="oromo-call-test-01",
        caller_hash="hash_oromo_01",
        language="om",
    )
    # Question: Is there rain in Bishoftu?
    response = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override="Bishooftuu keessatti roobni jiraa?",
    )
    assert response.metadata.grounded is True
    assert response.metadata.topic in ("weather_forecast", "weather_spraying")
    assert "Bishooftuu" in response.text
    assert "Naannoo" in response.text


@pytest.mark.asyncio
async def test_oromo_spraying_safety_query():
    """Verify pipeline handles chemical spraying inquiry in Afaan Oromo with safety analysis."""
    session = SessionState(
        session_id="oromo-call-test-02",
        caller_hash="hash_oromo_02",
        language="om",
    )
    # Question: Can I spray medicine in Adama tomorrow?
    response = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override="Boru Adaamaatti qoricha biifuu danda'aa?",
    )
    assert response.metadata.grounded is True
    assert response.metadata.topic == "weather_spraying"
    assert "Adaamaa" in response.text
    # Must contain agricultural safety recommendation in Oromo
    assert "qoricha" in response.text or "biifuuf" in response.text


@pytest.mark.asyncio
async def test_oromo_uncovered_safe_fallback():
    """Verify uncovered questions in Afaan Oromo trigger referral to 8028 and extension agent."""
    session = SessionState(
        session_id="oromo-call-test-03",
        caller_hash="hash_oromo_03",
        language="om",
    )
    # Off-topic question not covered by knowledge base
    response = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override="Mootummaan konkolaataa meeqaan gurgura?",
    )
    assert response.metadata.needs_referral is True
    assert "8028" in response.text
    assert "ogeessa qonnaa" in response.text


def test_oromo_post_call_sms_summary():
    """Verify post-call SMS advice summary format in Afaan Oromo."""
    advice = "Baga gara Heelo Faarmar nagaan dhuftan. Xaafii irratti lolaa baasaa."
    summary = generate_post_call_sms_summary(
        last_advice=advice,
        reached_answer=True,
        language="om",
    )
    assert summary.startswith("Heelo Faarmar: ")
    assert "Baga gara" not in summary
    assert "lolaa baasaa" in summary
