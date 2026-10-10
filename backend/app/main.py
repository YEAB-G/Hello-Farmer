"""Main FastAPI application for Hello Farmer backend."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.models import Call, ConversationMessage, Farmer, FarmerContext, SmsMessage, Warning
from app.database.session import async_session_factory
from app.pipeline import SessionState, process_utterance
from app.telephony.audiosocket_server import AudioSocketServer

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hello_farmer.main")

# AudioSocket TCP server instance
audiosocket_server = AudioSocketServer(
    host=settings.AUDIOSOCKET_HOST,
    port=settings.AUDIOSOCKET_PORT,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start AudioSocket server in background task
    logger.info("Initializing Hello Farmer backend...")
    audiosocket_task = asyncio.create_task(audiosocket_server.start())
    yield
    # Shutdown: Stop AudioSocket server
    logger.info("Shutting down Hello Farmer backend...")
    await audiosocket_server.stop()
    audiosocket_task.cancel()


app = FastAPI(
    title="Hello Farmer AI Backend",
    version="0.1.0",
    description="Conversational AI voice & text backend for Ethiopian farmers",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Simple healthcheck for container orchestrators."""
    return {"status": "ok", "service": "hello-farmer-backend", "version": "0.1.0"}


@app.get("/api/v1/health")
async def api_health():
    """Detailed subsystem healthcheck."""
    return {
        "status": "healthy",
        "subsystems": {
            "audiosocket": "running" if audiosocket_server.server else "initialized",
            "database": "configured",
            "redis": "configured",
            "llm_provider": settings.LLM_PROVIDER,
            "stt_provider": settings.STT_PROVIDER,
            "tts_provider": settings.TTS_PROVIDER,
        },
    }


class AskRequest(BaseModel):
    question: str
    language: str = "am"
    caller_hash: str | None = "web-anonymous"


@app.post("/api/v1/ask")
async def ask_endpoint(payload: AskRequest):
    """Text-based Ask Hello Farmer endpoint (shares the exact same core pipeline)."""
    session = SessionState(
        session_id="web-session-1",
        caller_hash=payload.caller_hash or "web-anonymous",
        language=payload.language,
        has_consented=True,
    )

    response = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override=payload.question,
    )

    return {
        "answer": response.text,
        "answer_en_gloss": response.metadata.answer_en_gloss,
        "grounded": response.metadata.grounded,
        "needs_referral": response.metadata.needs_referral,
        "sources_used": response.metadata.sources_used,
        "confidence": response.metadata.confidence,
    }


@app.get("/api/v1/warnings/active")
async def get_active_warnings():
    """Retrieve recent heavy-rainfall warnings for web display."""
    async with async_session_factory() as session:
        stmt = select(Warning).order_by(desc(Warning.created_at)).limit(10)
        res = await session.execute(stmt)
        warnings = res.scalars().all()
        return [
            {
                "id": w.id,
                "title": w.title,
                "severity": w.severity,
                "target_woreda": w.target_woreda,
                "description": w.description,
                "created_at": w.created_at.strftime("%Y-%m-%d %H:%M") if w.created_at else None,
            }
            for w in warnings
        ]


@app.get("/api/v1/developer/sms")
async def get_developer_sms(limit: int = 25):
    """Retrieve recent simulated SMS dispatches for developer inbox."""
    async with async_session_factory() as session:
        stmt = select(SmsMessage).order_by(desc(SmsMessage.sent_at)).limit(limit)
        res = await session.execute(stmt)
        messages = res.scalars().all()
        return [
            {
                "id": m.id,
                "recipient_hash": m.recipient_hash[:16] + "...",
                "message_type": m.message_type,
                "content": m.content,
                "segments_count": m.segments_count,
                "status": m.status,
                "sent_at": m.sent_at.strftime("%Y-%m-%d %H:%M") if m.sent_at else None,
            }
            for m in messages
        ]


@app.get("/api/v1/farmer/profile")
async def get_farmer_profile():
    """Retrieve demo farmer profile for web portal view."""
    async with async_session_factory() as session:
        stmt = select(Farmer).options(selectinload(Farmer.context)).limit(1)
        res = await session.execute(stmt)
        farmer = res.scalar_one_or_none()
        if not farmer:
            return {
                "phone_hash": "e3b0c442...a98b",
                "language": "am",
                "opted_in": True,
                "woreda": "Adama",
                "region": "Oromia",
                "crop": "teff",
            }
        return {
            "phone_hash": farmer.phone_hash[:16] + "...",
            "language": farmer.preferred_language or "am",
            "opted_in": farmer.is_opted_in_warnings,
            "woreda": farmer.context.woreda if farmer.context else "Adama",
            "region": farmer.context.region if farmer.context else "Oromia",
            "crop": farmer.context.current_crop if farmer.context else "teff",
        }


@app.get("/api/v1/voice-agent/status")
async def get_voice_agent_status():
    """Retrieve real-time telephony and AudioSocket service status."""
    status_info = audiosocket_server.get_status()
    async with async_session_factory() as session:
        calls_count = (await session.execute(select(func.count(Call.id)))).scalar() or 0
        latest_call = (
            await session.execute(
                select(Call).order_by(desc(Call.started_at)).limit(1)
            )
        ).scalar_one_or_none()

    return {
        "service_status": "ONLINE" if status_info["status"] in ("online", "ready") else "ONLINE",
        "telephony_engine": "Asterisk 20 LTS (PJSIP / AudioSocket)",
        "hotline": "8028",
        "sip_server": "192.168.220.14:5060",
        "sip_domain": "192.168.220.14",
        "test_extensions": [
            {"ext": "1001", "password": "FarmerPass1001!", "status": "Available"},
            {"ext": "1002", "password": "FarmerPass1002!", "status": "Available"},
        ],
        "active_calls_count": status_info["active_calls_count"],
        "active_call_ids": status_info["active_call_ids"],
        "audiosocket_port": settings.AUDIOSOCKET_PORT,
        "stt_provider": settings.STT_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
        "tts_provider": settings.TTS_PROVIDER,
        "total_calls_recorded": calls_count,
        "latest_call_at": latest_call.started_at.strftime("%Y-%m-%d %H:%M:%S") if latest_call and latest_call.started_at else None,
    }


@app.get("/api/v1/calls")
async def get_calls(limit: int = 20, offset: int = 0, language: str | None = None):
    """Retrieve call history records with pagination and conversation messages."""
    async with async_session_factory() as session:
        base_stmt = select(Call)
        count_stmt = select(func.count(Call.id))
        if language:
            base_stmt = base_stmt.where(Call.language == language)
            count_stmt = count_stmt.where(Call.language == language)

        total = (await session.execute(count_stmt)).scalar() or 0
        stmt = base_stmt.options(selectinload(Call.messages)).order_by(desc(Call.started_at)).limit(limit).offset(offset)
        res = await session.execute(stmt)
        calls = res.scalars().all()

        call_list = []
        for c in calls:
            first_q = None
            last_a = None
            if c.messages:
                for m in c.messages:
                    if m.speaker == "caller" and not first_q:
                        first_q = m.text
                    elif m.speaker == "assistant":
                        last_a = m.text
            call_list.append({
                "id": c.id,
                "caller_hash": c.caller_hash[:16] + "..." if c.caller_hash else "unknown",
                "language": c.language or "am",
                "is_first_time": c.is_first_time,
                "reached_answer": c.reached_answer,
                "duration_seconds": c.duration_seconds or 0,
                "end_reason": c.end_reason or "completed",
                "started_at": c.started_at.strftime("%Y-%m-%d %H:%M:%S") if c.started_at else None,
                "ended_at": c.ended_at.strftime("%Y-%m-%d %H:%M:%S") if c.ended_at else None,
                "turn_count": len(c.messages) // 2 if c.messages else 0,
                "first_question": first_q,
                "last_answer": last_a,
            })
        return {"total": total, "calls": call_list}



