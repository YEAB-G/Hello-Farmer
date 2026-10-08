"""Unit tests for Phase 6: Farmer context extraction, cryptographic privacy, and data deletion."""
import pytest
from backend.app.config import settings
from backend.app.farmer_context.extraction import (
    extract_context_from_utterance,
    merge_farmer_context,
)
from backend.app.farmer_context.profile import (
    decrypt_phone_number,
    delete_all_caller_data,
    encrypt_phone_number,
    get_or_create_farmer_profile,
    hash_phone_number,
    record_consent_decision,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_context_extraction_amharic():
    """Verify crop, symptoms, and location extraction from Amharic query."""
    text = "በአዳማ አካባቢ የጤፍ ሰብሌ ቅጠል ቢጫ ሆኗል ውሃ ማቆር ችግር አለ"
    ctx = extract_context_from_utterance(text, language="am")
    assert ctx.crop == "teff"
    assert "yellowing_leaves" in ctx.symptoms
    assert "waterlogging" in ctx.symptoms
    assert ctx.location == "Adama"


def test_context_extraction_oromo():
    """Verify crop and symptoms extraction from Afaan Oromo query."""
    text = "Boqqoolloo irratti dhibeen baalaa keelloo ta'eera"
    ctx = extract_context_from_utterance(text, language="om")
    assert ctx.crop == "maize"
    assert "yellowing_leaves" in ctx.symptoms


def test_context_merging_across_turns():
    """Verify conversational context accumulation across turns."""
    turn1_text = "ጤፍ ዘርቻለሁ"
    ctx1 = extract_context_from_utterance(turn1_text, language="am")
    memory = merge_farmer_context({}, ctx1)
    assert memory.get("crop") == "teff"

    turn2_text = "ቅጠሉ ቢጫ ሆኗል በአርሲ ነው ያለሁት"
    ctx2 = extract_context_from_utterance(turn2_text, language="am")
    memory = merge_farmer_context(memory, ctx2)
    assert memory.get("crop") == "teff"
    assert "yellowing_leaves" in memory.get("symptoms", [])
    assert memory.get("location") == "Arsi"


def test_phone_hashing_and_encryption():
    """Verify salted hashing is irreversible and encryption roundtrips."""
    phone = "+251911223344"
    h1 = hash_phone_number(phone)
    h2 = hash_phone_number(phone)
    assert h1 == h2
    assert len(h1) == 64
    assert phone not in h1

    # Fernet roundtrip
    enc = encrypt_phone_number(phone)
    assert enc != phone
    dec = decrypt_phone_number(enc)
    assert dec == phone


@pytest.mark.asyncio
async def test_database_profile_and_deletion_purge():
    """Verify farmer profile creation, consent logging, and complete data purge."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    test_caller_hash = "test_purge_hash_9876543210abcdef"

    async with session_factory() as session:
        # 1. Create Profile
        farmer = await get_or_create_farmer_profile(
            session=session,
            caller_hash=test_caller_hash,
            raw_phone="+251912345678",
            consented=True,
            preferred_language="am"
        )
        assert farmer.phone_hash == test_caller_hash
        assert farmer.encrypted_phone is not None

        # 2. Record Consent
        consent = await record_consent_decision(
            session=session,
            caller_hash=test_caller_hash,
            consented=True,
            scope="proactive_warnings"
        )
        assert consent.caller_hash == test_caller_hash

        # 3. Execute Complete Data Purge
        stats = await delete_all_caller_data(session=session, caller_hash=test_caller_hash)
        assert stats.get("farmers", 0) >= 1
        assert stats.get("consent_records", 0) >= 1

    await engine.dispose()
