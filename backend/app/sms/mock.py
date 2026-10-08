"""Mock SMS provider that persists to database and outputs to developer console."""
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database.models import SmsMessage
from app.database.session import async_session_factory
from app.sms.base import BaseSMSProvider, SMSDeliveryReport
from app.sms.encoding import encode_and_truncate_sms

logger = logging.getLogger("hello_farmer.sms.mock")


class MockSMSProvider(BaseSMSProvider):
    """Zero-cost mock SMS provider with duplicate suppression and DB storage."""

    def __init__(self, suppress_duplicates_hours: int = 24):
        self.suppress_duplicates_hours = suppress_duplicates_hours

    async def send_sms(
        self,
        recipient_phone_or_hash: str,
        text: str,
        message_type: str = "summary",
        max_segments: int = 2,
    ) -> SMSDeliveryReport:
        """Deliver or simulate delivery of SMS message."""
        # 1. Encode and truncate text
        encoding_res = encode_and_truncate_sms(text, max_segments=max_segments)
        clean_text = encoding_res.text

        msg_id = str(uuid.uuid4())

        # 2. Check duplicate suppression in DB
        async with async_session_factory() as session:
            since = datetime.utcnow() - timedelta(hours=self.suppress_duplicates_hours)
            stmt = select(SmsMessage).where(
                SmsMessage.recipient_hash == recipient_phone_or_hash,
                SmsMessage.message_type == message_type,
                SmsMessage.content == clean_text,
                SmsMessage.sent_at >= since,
            ).limit(1)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(
                    f"[MOCK SMS] Duplicate message suppressed for {recipient_phone_or_hash[:8]}... (type={message_type})"
                )
                return SMSDeliveryReport(
                    recipient_hash=recipient_phone_or_hash,
                    segments_count=encoding_res.segment_count,
                    status="DUPLICATE_SUPPRESSED",
                    provider_message_id=existing.id,
                    encoding=encoding_res.encoding,
                )

            # 3. Insert new SMS record
            sms_record = SmsMessage(
                id=msg_id,
                recipient_hash=recipient_phone_or_hash,
                message_type=message_type,
                content=clean_text,
                segments_count=encoding_res.segment_count,
                status="SENT",
                sent_at=datetime.utcnow(),
            )
            session.add(sms_record)
            await session.commit()

        # 4. Print prominent developer console banner
        banner = (
            "\n" + "=" * 60 + "\n"
            f"[MOCK SMS DISPATCHED]\n"
            f"Message ID: {msg_id}\n"
            f"To (Hash):  {recipient_phone_or_hash}\n"
            f"Type:       {message_type}\n"
            f"Encoding:   {encoding_res.encoding} ({encoding_res.segment_count} segment(s), {encoding_res.char_count} chars)\n"
            f"Content:    {clean_text}\n"
            + "=" * 60 + "\n"
        )
        print(banner)
        logger.info(f"Mock SMS sent to {recipient_phone_or_hash[:8]}...: {clean_text[:40]}...")

        return SMSDeliveryReport(
            recipient_hash=recipient_phone_or_hash,
            segments_count=encoding_res.segment_count,
            status="SENT",
            provider_message_id=msg_id,
            encoding=encoding_res.encoding,
        )


def get_sms_provider() -> BaseSMSProvider:
    """Return configured SMS provider."""
    return MockSMSProvider()
