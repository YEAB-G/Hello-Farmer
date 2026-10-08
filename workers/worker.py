"""Background worker definitions using arq."""
import logging
import os

from arq.connections import RedisSettings

try:
    from app.sms.mock import get_sms_provider
    from app.sms.summary import generate_post_call_sms_summary
except ImportError:
    from backend.app.sms.mock import get_sms_provider
    from backend.app.sms.summary import generate_post_call_sms_summary

logger = logging.getLogger("hello_farmer.worker")


async def generate_post_call_summary(
    ctx,
    call_id: str,
    caller_hash: str,
    language: str = "am",
    last_advice: str | None = None,
    reached_answer: bool = True,
    crop: str | None = None,
):
    """Generate post-call summary and dispatch mock SMS delivery."""
    logger.info(f"Worker generating post-call SMS summary for call_id={call_id}, recipient={caller_hash[:8]}...")
    summary_text = generate_post_call_sms_summary(
        last_advice=last_advice,
        reached_answer=reached_answer,
        language=language,
        crop=crop,
    )
    sms_provider = get_sms_provider()
    report = await sms_provider.send_sms(
        recipient_phone_or_hash=caller_hash,
        text=summary_text,
        message_type="summary",
        max_segments=2,
    )
    logger.info(
        f"Post-call SMS dispatched for call {call_id}: status={report.status}, segments={report.segments_count}"
    )
    return {
        "status": report.status,
        "call_id": call_id,
        "segments": report.segments_count,
        "message_id": report.provider_message_id,
    }


async def evaluate_weather_warnings(ctx, location_name: str = "Adama"):
    """Evaluate weather forecast against heavy rainfall threshold and dispatch warnings."""
    logger.info(f"Worker evaluating weather warnings for location={location_name}...")
    from app.weather.location import resolve_location
    from app.weather.provider import get_weather_provider
    from app.weather.risk import WeatherRiskAnalyzer

    loc = resolve_location(location_name)
    if not loc:
        return {"status": "skipped", "reason": "location_not_found"}

    provider = get_weather_provider()
    forecast = await provider.get_forecast(loc.latitude, loc.longitude, loc.name)

    is_heavy = WeatherRiskAnalyzer.is_heavy_rainfall_hazard(forecast)
    return {
        "status": "completed",
        "location": loc.name,
        "is_heavy_rain": is_heavy,
        "precipitation_mm": forecast.precipitation_sum_mm,
    }


async def startup(ctx):
    logger.info("Starting Hello Farmer arq background worker...")


async def shutdown(ctx):
    logger.info("Shutting down Hello Farmer arq background worker...")


class WorkerSettings:
    functions = [generate_post_call_summary, evaluate_weather_warnings]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
    )
