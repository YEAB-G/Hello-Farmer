"""Abstract interface for SMS providers."""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class SMSDeliveryReport(BaseModel):
    recipient_hash: str
    segments_count: int
    status: str
    provider_message_id: str
    encoding: str  # UCS-2 or GSM-7


class BaseSMSProvider(ABC):
    @abstractmethod
    async def send_sms(self, recipient_phone_or_hash: str, text: str, message_type: str = "summary") -> SMSDeliveryReport:
        """Deliver or simulate delivery of SMS message."""
