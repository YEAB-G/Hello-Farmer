"""Unit tests for Phase 8: SMS encoding, segmentation, mock provider, and post-call summaries."""
import pytest
from sqlalchemy import select

from app.database.models import SmsMessage
from app.database.session import async_session_factory
from app.sms.dispatcher import trigger_post_call_summary
from app.sms.encoding import (
    calculate_segments,
    encode_and_truncate_sms,
    is_gsm7,
)
from app.sms.mock import MockSMSProvider
from app.sms.summary import generate_post_call_sms_summary


def test_sms_encoding_detection():
    """Verify charset detection: GSM-7 for Latin vs UCS-2 for Ge'ez."""
    text_latin = "Heelo Faarmar: Baalli keelloo yoo ta'e bishaan dhangalaasaa."
    assert is_gsm7(text_latin) is True

    text_geez = "ሄሎ ፋርመር፡ የጤፍ ቅጠል ቢጫ ሲሆን የቦይ ማውጣት ዘዴ ይጠቀሙ።"
    assert is_gsm7(text_geez) is False


def test_sms_segment_calculation():
    """Verify segment limits: 160 chars for GSM-7 vs 70 chars for UCS-2."""
    # GSM-7 single vs multi
    latin_100 = "A" * 100
    assert calculate_segments(latin_100, "GSM-7") == 1

    latin_200 = "A" * 200
    assert calculate_segments(latin_200, "GSM-7") == 2

    # UCS-2 single vs multi
    geez_50 = "ጤ" * 50
    assert calculate_segments(geez_50, "UCS-2") == 1

    geez_100 = "ጤ" * 100
    assert calculate_segments(geez_100, "UCS-2") == 2


def test_sms_safe_truncation_preserves_words():
    """Verify long Ge'ez text is safely truncated within segment bounds without breaking words."""
    long_geez = (
        "ሄሎ ፋርመር፡ የጤፍ ሰብልዎ ላይ የታየው ቢጫ ቅጠል በውሃ ማቆር ምክንያት ሊሆን ስለሚችል "
        "በማሳዎ ላይ የጎርፍ ማስተንፈሻ ቦይ በማውጣት ውሃውን እንዲፈስ ያድርጉ። "
        "ይህ ካልረዳ የአካባቢዎን የግብርና ባለሙያ ያማክሩ።"
    )
    result = encode_and_truncate_sms(long_geez, max_segments=2)
    assert result.encoding == "UCS-2"
    assert result.segment_count <= 2
    assert result.is_truncated is True
    assert result.text.endswith("...")
    # Assert length within 2-segment UCS-2 boundary (2 * 67 = 134)
    assert len(result.text) <= 134


def test_post_call_summary_formatting():
    """Verify post-call summary strips greetings and formats advice."""
    advice_am = "እንኳን ወደ ሄሎ ፋርመር በደህና መጡ። የጤፍ ቅጠል ቢጫ ሲሆን ውሃ ማፍሰሻ ቦይ ያዘጋጁ።"
    summary_am = generate_post_call_sms_summary(advice_am, reached_answer=True, language="am")
    assert "እንኳን ወደ ሄሎ ፋርመር" not in summary_am
    assert "ሄሎ ፋርመር፡" in summary_am
    assert "ውሃ ማፍሰሻ ቦይ ያዘጋጁ" in summary_am

    advice_om = "Baga gara Heelo Faarmar nagaan dhuftan. Bo'oo lolaa baasaa."
    summary_om = generate_post_call_sms_summary(advice_om, reached_answer=True, language="om")
    assert "Baga gara Heelo Faarmar" not in summary_om
    assert "Heelo Faarmar:" in summary_om
    assert "Bo'oo lolaa baasaa" in summary_om


def test_post_call_summary_unreached_fallback():
    """Verify ungrounded call produces safe referral in summary."""
    summary_fallback_am = generate_post_call_sms_summary(None, reached_answer=False, language="am")
    assert "8028" in summary_fallback_am
    assert "ባለሙያ" in summary_fallback_am

    summary_fallback_om = generate_post_call_sms_summary(None, reached_answer=False, language="om")
    assert "8028" in summary_fallback_om
    assert "ogeessa qonnaa" in summary_fallback_om


@pytest.mark.asyncio
async def test_mock_sms_delivery_and_persistence():
    """Verify MockSMSProvider writes SMS message to PostgreSQL database."""
    provider = MockSMSProvider()
    import uuid
    test_hash = f"farmer_recipient_test_{uuid.uuid4().hex[:8]}"
    content = "ሄሎ ፋርመር፡ የጤፍ ዘር ጥልቀት አንድ ሴንቲሜትር ይሁን።"

    report = await provider.send_sms(
        recipient_phone_or_hash=test_hash,
        text=content,
        message_type="summary",
    )
    assert report.status == "SENT"
    assert report.encoding == "UCS-2"
    assert report.segments_count >= 1

    # Verify presence in database
    async with async_session_factory() as session:
        stmt = select(SmsMessage).where(SmsMessage.id == report.provider_message_id)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.recipient_hash == test_hash
        assert record.content == content
        assert record.status == "SENT"


@pytest.mark.asyncio
async def test_mock_sms_duplicate_suppression():
    """Verify sending identical message to same recipient within 24h is suppressed."""
    provider = MockSMSProvider()
    import uuid
    test_hash = f"farmer_dupe_test_{uuid.uuid4().hex[:8]}"
    content = "ሄሎ ፋርመር፡ ነገ ዝናብ ስለሚጠበቅ ኬሚካል አይርጩ።"

    # First send: should succeed
    rep1 = await provider.send_sms(recipient_phone_or_hash=test_hash, text=content, message_type="warning")
    assert rep1.status == "SENT"

    # Second send: should be suppressed
    rep2 = await provider.send_sms(recipient_phone_or_hash=test_hash, text=content, message_type="warning")
    assert rep2.status == "DUPLICATE_SUPPRESSED"


@pytest.mark.asyncio
async def test_post_call_dispatcher_execution():
    """Verify post-call summary dispatcher triggers asynchronously without exception."""
    res = await trigger_post_call_summary(
        call_id="call-test-dispatch-999",
        caller_hash="caller_hash_dispatch_999",
        language="am",
        last_advice="የስንዴ ቢጫ ዋግ ሲታይ የግብርና ባለሙያ ያማክሩ።",
        reached_answer=True,
    )
    assert res is not None
    assert "status" in res
