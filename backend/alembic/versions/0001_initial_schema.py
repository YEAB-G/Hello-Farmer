"""Baseline initial schema with pgvector and HNSW index.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-08 20:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Farmers
    if "farmers" not in existing_tables:
        op.create_table(
            "farmers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("phone_hash", sa.String(64), nullable=False),
            sa.Column("encrypted_phone", sa.Text(), nullable=True),
            sa.Column("preferred_language", sa.String(10), server_default="am"),
            sa.Column("is_opted_in_warnings", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_farmers_phone_hash", "farmers", ["phone_hash"], unique=True)

    # 2. Farmer Context
    if "farmer_context" not in existing_tables:
        op.create_table(
            "farmer_context",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id"), nullable=False),
            sa.Column("current_crop", sa.String(100), nullable=True),
            sa.Column("growth_stage", sa.String(100), nullable=True),
            sa.Column("symptoms", sa.Text(), nullable=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("woreda", sa.String(100), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_farmer_context_farmer_id", "farmer_context", ["farmer_id"])

    # 3. Farmer Crops
    if "farmer_crops" not in existing_tables:
        op.create_table(
            "farmer_crops",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id"), nullable=False),
            sa.Column("crop_name", sa.String(100), nullable=False),
            sa.Column("variety", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_farmer_crops_farmer_id", "farmer_crops", ["farmer_id"])

    # 4. Calls
    if "calls" not in existing_tables:
        op.create_table(
            "calls",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("caller_hash", sa.String(64), nullable=False),
            sa.Column("is_first_time", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("language", sa.String(10), server_default="am"),
            sa.Column("reached_answer", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("end_reason", sa.String(50), nullable=True),
            sa.Column("time_to_first_answer_ms", sa.Integer(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), server_default=sa.text("0")),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("location_name", sa.String(100), nullable=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("zone", sa.String(100), nullable=True),
            sa.Column("woreda", sa.String(100), nullable=True),
            sa.Column("location_confidence", sa.Float(), nullable=True),
            sa.Column("agroecological_zone", sa.String(50), nullable=True),
            sa.Column("recording_consent_status", sa.String(50), server_default="notice_announced"),
        )
        op.create_index("ix_calls_caller_hash", "calls", ["caller_hash"])

    # 5. Conversation Messages
    if "conversation_messages" not in existing_tables:
        op.create_table(
            "conversation_messages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("call_id", sa.String(36), sa.ForeignKey("calls.id"), nullable=False),
            sa.Column("speaker", sa.String(20), nullable=False),
            sa.Column("text", sa.Text(), nullable=True),
            sa.Column("audio_path", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_conversation_messages_call_id", "conversation_messages", ["call_id"])

    # 6. Agricultural Documents
    if "agricultural_documents" not in existing_tables:
        op.create_table(
            "agricultural_documents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("publisher", sa.String(255), nullable=True),
            sa.Column("publication_year", sa.Integer(), nullable=True),
            sa.Column("source_tier", sa.Integer(), nullable=False),
            sa.Column("language", sa.String(10), server_default="am"),
            sa.Column("file_path", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # 7. Knowledge Chunks with Vector(768) and HNSW Index
    if "knowledge_chunks" not in existing_tables:
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("document_id", sa.String(36), sa.ForeignKey("agricultural_documents.id"), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", Vector(768), nullable=True),
            sa.Column("crop", sa.String(100), nullable=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("topic", sa.String(100), nullable=True),
            sa.Column("source_tier", sa.Integer(), server_default=sa.text("1")),
            sa.Column("page_number", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
        op.create_index("ix_knowledge_chunks_crop", "knowledge_chunks", ["crop"])

    # Ensure HNSW cosine index exists on knowledge_chunks
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);"
    )

    # 8. Weather Records
    if "weather_records" not in existing_tables:
        op.create_table(
            "weather_records",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("location_name", sa.String(100), nullable=True),
            sa.Column("precipitation_mm", sa.Float(), server_default=sa.text("0.0")),
            sa.Column("temperature_c", sa.Float(), server_default=sa.text("20.0")),
            sa.Column("forecast_time", sa.DateTime(), nullable=False),
            sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # 9. Warnings
    if "warnings" not in existing_tables:
        op.create_table(
            "warnings",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("warning_type", sa.String(50), server_default="heavy_rainfall"),
            sa.Column("severity", sa.String(20), server_default="MEDIUM"),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("target_region", sa.String(100), nullable=True),
            sa.Column("target_woreda", sa.String(100), nullable=True),
            sa.Column("valid_until", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # 10. Farmer Warnings
    if "farmer_warnings" not in existing_tables:
        op.create_table(
            "farmer_warnings",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("warning_id", sa.String(36), sa.ForeignKey("warnings.id"), nullable=False),
            sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id"), nullable=False),
            sa.Column("delivery_status", sa.String(20), server_default="PENDING"),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
        )

    # 11. SMS Messages
    if "sms_messages" not in existing_tables:
        op.create_table(
            "sms_messages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("recipient_hash", sa.String(64), nullable=False),
            sa.Column("message_type", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("segments_count", sa.Integer(), server_default=sa.text("1")),
            sa.Column("status", sa.String(20), server_default="SENT"),
            sa.Column("sent_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_sms_messages_recipient_hash", "sms_messages", ["recipient_hash"])

    # 12. Supporting Tables: web_notifications, ai_interactions, consent_records, place_names, quota_usage
    if "web_notifications" not in existing_tables:
        op.create_table(
            "web_notifications",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("farmer_id", sa.String(36), sa.ForeignKey("farmers.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "ai_interactions" not in existing_tables:
        op.create_table(
            "ai_interactions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("call_id", sa.String(36), nullable=True),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("model", sa.String(50), nullable=False),
            sa.Column("latency_ms", sa.Integer(), nullable=False),
            sa.Column("grounded", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "consent_records" not in existing_tables:
        op.create_table(
            "consent_records",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("caller_hash", sa.String(64), nullable=False),
            sa.Column("consent_type", sa.String(50), server_default="call_recording_and_storage"),
            sa.Column("voice_confirmed", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("consented_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "place_names" not in existing_tables:
        op.create_table(
            "place_names",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("name_am", sa.String(100), nullable=True),
            sa.Column("name_om", sa.String(100), nullable=True),
            sa.Column("aliases", sa.Text(), nullable=True),
            sa.Column("region", sa.String(100), nullable=False),
            sa.Column("zone", sa.String(100), nullable=True),
            sa.Column("woreda", sa.String(100), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=False),
            sa.Column("longitude", sa.Float(), nullable=False),
            sa.Column("provenance", sa.String(100), server_default="CSA_Ethiopia"),
        )
        op.create_index("ix_place_names_name", "place_names", ["name"])

    if "quota_usage" not in existing_tables:
        op.create_table(
            "quota_usage",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("service_name", sa.String(50), nullable=False),
            sa.Column("usage_date", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("count", sa.Integer(), server_default=sa.text("1")),
        )


def downgrade() -> None:
    # Downgrade drops tables in reverse dependency order
    op.execute("DROP TABLE IF EXISTS quota_usage CASCADE;")
    op.execute("DROP TABLE IF EXISTS place_names CASCADE;")
    op.execute("DROP TABLE IF EXISTS consent_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_interactions CASCADE;")
    op.execute("DROP TABLE IF EXISTS web_notifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS sms_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS farmer_warnings CASCADE;")
    op.execute("DROP TABLE IF EXISTS warnings CASCADE;")
    op.execute("DROP TABLE IF EXISTS weather_records CASCADE;")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks CASCADE;")
    op.execute("DROP TABLE IF EXISTS agricultural_documents CASCADE;")
    op.execute("DROP TABLE IF EXISTS conversation_messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS calls CASCADE;")
    op.execute("DROP TABLE IF EXISTS farmer_crops CASCADE;")
    op.execute("DROP TABLE IF EXISTS farmer_context CASCADE;")
    op.execute("DROP TABLE IF EXISTS farmers CASCADE;")
