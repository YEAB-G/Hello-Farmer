"""Farmer profile management, cryptographic privacy, and data deletion handlers.

Implements Section 6.9 rules:
- Salted SHA-256 phone hashing for privacy by default.
- AES-256 (Fernet) encryption at rest for phone numbers when explicit spoken consent is given.
- Zero plaintext phone storage for non-consenting users.
- Caller data deletion by caller_hash.
"""
import hashlib
import logging
from typing import Optional

from backend.app.config import settings
from backend.app.database.models import (
    Call,
    ConsentRecord,
    ConversationMessage,
    Farmer,
    FarmerContext,
    FarmerCrop,
    FarmerWarning,
    SmsMessage,
)
from cryptography.fernet import Fernet
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("hello_farmer.privacy")


def hash_phone_number(raw_phone: str) -> str:
    """Compute salted SHA-256 hash of phone number."""
    salt = settings.SALT_HASH_SECRET
    clean = raw_phone.strip().replace(" ", "").replace("-", "")
    return hashlib.sha256(f"{salt}:{clean}".encode("utf-8")).hexdigest()


def get_fernet_cipher() -> Fernet:
    """Get Fernet cipher instance from environment encryption key."""
    key = settings.PHONE_ENCRYPTION_KEY
    if not key or len(key) < 32:
        key = Fernet.generate_key()
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt_phone_number(raw_phone: str) -> str:
    """Encrypt phone number at rest using AES-256 Fernet."""
    cipher = get_fernet_cipher()
    return cipher.encrypt(raw_phone.strip().encode("utf-8")).decode("utf-8")


def decrypt_phone_number(encrypted_phone: str) -> str:
    """Decrypt phone number from rest."""
    cipher = get_fernet_cipher()
    return cipher.decrypt(encrypted_phone.encode("utf-8")).decode("utf-8")


async def get_or_create_farmer_profile(
    session: AsyncSession,
    caller_hash: str,
    raw_phone: Optional[str] = None,
    consented: bool = False,
    preferred_language: str = "am"
) -> Farmer:
    """Retrieve existing farmer profile or initialize a privacy-preserving record."""
    stmt = select(Farmer).where(Farmer.phone_hash == caller_hash)
    result = await session.execute(stmt)
    farmer = result.scalar_one_or_none()

    if not farmer:
        enc_phone = encrypt_phone_number(raw_phone) if (consented and raw_phone) else None
        farmer = Farmer(
            phone_hash=caller_hash,
            encrypted_phone=enc_phone,
            is_opted_in_warnings=consented,
            preferred_language=preferred_language,
        )
        session.add(farmer)
        await session.commit()
        await session.refresh(farmer)
        logger.info(f"Initialized new farmer record for phone_hash: {caller_hash[:8]}... (Consented: {consented})")
    else:
        if consented and not farmer.is_opted_in_warnings:
            farmer.is_opted_in_warnings = True
            if raw_phone:
                farmer.encrypted_phone = encrypt_phone_number(raw_phone)
            await session.commit()
            await session.refresh(farmer)

    return farmer


async def record_consent_decision(
    session: AsyncSession,
    caller_hash: str,
    consented: bool,
    scope: str = "call_recording_and_storage"
) -> ConsentRecord:
    """Persist spoken consent decision in audit table."""
    consent = ConsentRecord(
        caller_hash=caller_hash,
        voice_confirmed=consented,
        consent_type=scope,
    )
    session.add(consent)
    await session.commit()
    logger.info(f"Recorded consent ({consented}) for caller_hash {caller_hash[:8]}...")
    return consent


async def delete_all_caller_data(session: AsyncSession, caller_hash: str) -> dict[str, int]:
    """Purge all records associated with caller_hash (Right to be Forgotten).

    Returns summary count of deleted records across all tables.
    """
    logger.warning(f"Executing complete data purge for caller_hash: {caller_hash[:8]}...")
    stats = {}

    # 1. Delete SMS messages
    res = await session.execute(delete(SmsMessage).where(SmsMessage.recipient_hash == caller_hash))
    stats["sms_messages"] = res.rowcount

    # 2. Delete Farmer and linked records
    farmer_res = await session.execute(select(Farmer.id).where(Farmer.phone_hash == caller_hash))
    farmer_ids = [f[0] for f in farmer_res.all()]
    if farmer_ids:
        await session.execute(delete(FarmerWarning).where(FarmerWarning.farmer_id.in_(farmer_ids)))
        await session.execute(delete(FarmerContext).where(FarmerContext.farmer_id.in_(farmer_ids)))
        await session.execute(delete(FarmerCrop).where(FarmerCrop.farmer_id.in_(farmer_ids)))
        f_del = await session.execute(delete(Farmer).where(Farmer.id.in_(farmer_ids)))
        stats["farmers"] = f_del.rowcount
    else:
        stats["farmers"] = 0

    # 3. Delete Calls and Conversation Messages
    call_ids_res = await session.execute(select(Call.id).where(Call.caller_hash == caller_hash))
    call_ids = [c[0] for c in call_ids_res.all()]
    if call_ids:
        msg_del = await session.execute(
            delete(ConversationMessage).where(ConversationMessage.call_id.in_(call_ids))
        )
        stats["conversation_messages"] = msg_del.rowcount
    else:
        stats["conversation_messages"] = 0

    res = await session.execute(delete(Call).where(Call.caller_hash == caller_hash))
    stats["calls"] = res.rowcount

    # 4. Delete Consent Records
    res = await session.execute(delete(ConsentRecord).where(ConsentRecord.caller_hash == caller_hash))
    stats["consent_records"] = res.rowcount

    await session.commit()
    logger.info(f"Purge complete for {caller_hash[:8]}... Deleted stats: {stats}")
    return stats
