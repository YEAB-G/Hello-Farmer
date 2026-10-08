"""Post-call SMS job dispatcher to queue background summarization."""
import asyncio
import logging
import os

from app.sms.mock import get_sms_provider
from app.sms.summary import generate_post_call_sms_summary

logger = logging.getLogger("hello_farmer.sms.dispatcher")


async def trigger_post_call_summary(
    call_id: str,
    caller_hash: str,
    language: str = "am",
    last_advice: str | None = None,
    reached_answer: bool = True,
    crop: str | None = None,
) -> dict:
    """Queue post-call SMS summary job via Redis/arq or execute in background asyncio task."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        redis_settings = RedisSettings(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
        )
        redis_pool = await create_pool(redis_settings)
        job = await redis_pool.enqueue_job(
            "generate_post_call_summary",
            call_id,
            caller_hash,
            language,
            last_advice,
            reached_answer,
            crop,
        )
        if hasattr(redis_pool, "aclose"):
            await redis_pool.aclose()
        else:
            await redis_pool.close()
        return {"status": "enqueued", "job_id": job.job_id}
    except Exception as exc:
        logger.warning(f"Could not connect to Redis/arq queue ({exc}); running post-call SMS directly: {call_id}")

        async def _direct_send():
            try:
                summary_text = generate_post_call_sms_summary(
                    last_advice=last_advice,
                    reached_answer=reached_answer,
                    language=language,
                    crop=crop,
                )
                provider = get_sms_provider()
                await provider.send_sms(
                    recipient_phone_or_hash=caller_hash,
                    text=summary_text,
                    message_type="summary",
                    max_segments=2,
                )
            except Exception as e:
                logger.error(f"Direct post-call SMS execution failed: {e}")

        asyncio.create_task(_direct_send())
        return {"status": "direct_dispatched"}
