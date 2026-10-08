"""SQLAlchemy models for Hello Farmer database schema."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_hash = Column(String(64), unique=True, nullable=False, index=True)
    encrypted_phone = Column(Text, nullable=True)  # Fernet encrypted, only if opted in
    preferred_language = Column(String(10), default="am")
    is_opted_in_warnings = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    context = relationship("FarmerContext", back_populates="farmer", uselist=False)
    crops = relationship("FarmerCrop", back_populates="farmer")
    warnings = relationship("FarmerWarning", back_populates="farmer")


class FarmerContext(Base):
    __tablename__ = "farmer_context"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id"), nullable=False, index=True)
    current_crop = Column(String(100), nullable=True)
    growth_stage = Column(String(100), nullable=True)
    symptoms = Column(Text, nullable=True)
    region = Column(String(100), nullable=True)
    woreda = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="context")


class FarmerCrop(Base):
    __tablename__ = "farmer_crops"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id"), nullable=False, index=True)
    crop_name = Column(String(100), nullable=False)
    variety = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farmer = relationship("Farmer", back_populates="crops")


class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    caller_hash = Column(String(64), nullable=False, index=True)
    is_first_time = Column(Boolean, default=True)
    language = Column(String(10), default="am")
    reached_answer = Column(Boolean, default=False)  # Grounded answer reached
    fallback_used = Column(Boolean, default=False)
    end_reason = Column(String(50), nullable=True)  # caller_hangup, max_silence, timeout, error
    time_to_first_answer_ms = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    messages = relationship("ConversationMessage", back_populates="call")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    call_id = Column(String(36), ForeignKey("calls.id"), nullable=False, index=True)
    speaker = Column(String(20), nullable=False)  # caller or assistant
    text = Column(Text, nullable=True)
    audio_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="messages")


class AgriculturalDocument(Base):
    __tablename__ = "agricultural_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    source_tier = Column(Integer, nullable=False)  # 1 (Gov/EIAR), 2 (FAO/CGIAR), 3 (Academic)
    language = Column(String(10), default="am")
    file_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("KnowledgeChunk", back_populates="document")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("agricultural_documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)  # 768 dimensions for Gemini text-embedding-004
    crop = Column(String(100), nullable=True, index=True)

    region = Column(String(100), nullable=True)
    topic = Column(String(100), nullable=True)
    source_tier = Column(Integer, default=1)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("AgriculturalDocument", back_populates="chunks")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String(100), nullable=True)
    precipitation_mm = Column(Float, default=0.0)
    temperature_c = Column(Float, default=20.0)
    forecast_time = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)


class Warning(Base):
    __tablename__ = "warnings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    warning_type = Column(String(50), default="heavy_rainfall")
    severity = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    target_region = Column(String(100), nullable=True)
    target_woreda = Column(String(100), nullable=True)
    valid_until = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FarmerWarning(Base):
    __tablename__ = "farmer_warnings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    warning_id = Column(String(36), ForeignKey("warnings.id"), nullable=False, index=True)
    farmer_id = Column(String(36), ForeignKey("farmers.id"), nullable=False, index=True)
    delivery_status = Column(String(20), default="PENDING")
    delivered_at = Column(DateTime, nullable=True)

    farmer = relationship("Farmer", back_populates="warnings")


class SmsMessage(Base):
    __tablename__ = "sms_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_hash = Column(String(64), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)  # summary or warning
    content = Column(Text, nullable=False)
    segments_count = Column(Integer, default=1)
    status = Column(String(20), default="SENT")
    sent_at = Column(DateTime, default=datetime.utcnow)


class WebNotification(Base):
    __tablename__ = "web_notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmers.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AiInteraction(Base):
    __tablename__ = "ai_interactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    call_id = Column(String(36), nullable=True, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    latency_ms = Column(Integer, nullable=False)
    grounded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    caller_hash = Column(String(64), nullable=False, index=True)
    consent_type = Column(String(50), default="call_recording_and_storage")
    voice_confirmed = Column(Boolean, default=False)
    consented_at = Column(DateTime, default=datetime.utcnow)


class PlaceName(Base):
    __tablename__ = "place_names"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    name_am = Column(String(100), nullable=True)
    name_om = Column(String(100), nullable=True)
    aliases = Column(Text, nullable=True)
    region = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=True)
    woreda = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    provenance = Column(String(100), default="CSA_Ethiopia")


class QuotaUsage(Base):
    __tablename__ = "quota_usage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service_name = Column(String(50), nullable=False)
    usage_date = Column(DateTime, default=datetime.utcnow)
    count = Column(Integer, default=1)
