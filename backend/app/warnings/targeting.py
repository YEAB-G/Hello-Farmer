"""Targeting engine for heavy-rainfall warnings.

Enforces:
1. Opt-in verification (Farmer.is_opted_in_warnings == True).
2. Geographic matching (FarmerContext woreda/region matches affected zone).
3. Daily frequency cap (maximum 1 warning per farmer per 24 hours).
4. Duplicate warning suppression.
5. Dual delivery: Mock SMS + WebNotification database record.
"""
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Farmer, FarmerContext, FarmerWarning, Warning, WebNotification
from app.sms.mock import get_sms_provider
from app.warnings.generate import generate_rainfall_warning_content
from app.warnings.rules import HeavyRainfallRules
from app.weather.base import WeatherForecast

logger = logging.getLogger("hello_farmer.warnings.targeting")


class WarningTargetingEngine:
    """Evaluates forecasts and targets eligible opt-in farmers."""

    DAILY_WARNING_CAP = 1

    @classmethod
    async def process_location_warning(
        cls,
        location_name: str,
        forecast: WeatherForecast,
        session: AsyncSession,
    ) -> dict:
        """Classify rainfall, identify targeted farmers, and dispatch notifications."""
        classification = HeavyRainfallRules.evaluate(forecast)

        if not classification.is_active:
            return {
                "location": location_name,
                "warning_active": False,
                "severity": "NONE",
                "delivered": 0,
            }

        # 1. Create or retrieve Warning record
        now = datetime.utcnow()
        valid_until = now + timedelta(days=2)

        # Check existing warning in DB
        w_stmt = select(Warning).where(
            Warning.target_woreda == location_name,
            Warning.severity == classification.severity,
            Warning.valid_until >= now,
        ).limit(1)
        res = await session.execute(w_stmt)
        warning_obj = res.scalar_one_or_none()

        if not warning_obj:
            content_am = generate_rainfall_warning_content(
                location_name=location_name,
                severity=classification.severity,
                rainfall_mm=classification.max_daily_rainfall_mm,
                language="am",
            )
            warning_obj = Warning(
                id=str(uuid.uuid4()),
                warning_type="heavy_rainfall",
                severity=classification.severity,
                title=content_am.title,
                description=content_am.description,
                target_region="Ethiopia",
                target_woreda=location_name,
                valid_until=valid_until,
                created_at=now,
            )
            session.add(warning_obj)
            await session.flush()

        # 2. Find eligible opt-in farmers in the affected area
        f_stmt = (
            select(Farmer)
            .join(FarmerContext, Farmer.id == FarmerContext.farmer_id)
            .options(selectinload(Farmer.context))
            .where(
                Farmer.is_opted_in_warnings.is_(True),
                (FarmerContext.woreda.ilike(f"%{location_name}%") | FarmerContext.region.ilike(f"%{location_name}%")),
            )
        )
        farmers_res = await session.execute(f_stmt)
        eligible_farmers = farmers_res.scalars().all()

        delivered_count = 0
        cap_suppressed_count = 0
        dupe_suppressed_count = 0

        sms_provider = get_sms_provider()

        for farmer in eligible_farmers:
            # 3. Check duplicate suppression for this specific warning
            dupe_stmt = select(FarmerWarning).where(
                FarmerWarning.warning_id == warning_obj.id,
                FarmerWarning.farmer_id == farmer.id,
            ).limit(1)
            dupe_res = await session.execute(dupe_stmt)
            if dupe_res.scalar_one_or_none():
                dupe_suppressed_count += 1
                continue

            # 4. Check per-farmer daily cap (max 1 warning in 24 hours)
            day_ago = now - timedelta(hours=24)
            cap_stmt = select(FarmerWarning).where(
                FarmerWarning.farmer_id == farmer.id,
                FarmerWarning.delivered_at >= day_ago,
            )
            cap_res = await session.execute(cap_stmt)
            recent_warnings = cap_res.scalars().all()
            if len(recent_warnings) >= cls.DAILY_WARNING_CAP:
                cap_suppressed_count += 1
                logger.info(f"Daily warning cap reached for farmer {farmer.id[:8]}... (suppressed)")
                continue

            # 5. Generate localized notification content
            farmer_lang = farmer.preferred_language or "am"
            localized = generate_rainfall_warning_content(
                location_name=location_name,
                severity=classification.severity,
                rainfall_mm=classification.max_daily_rainfall_mm,
                language=farmer_lang,
            )

            # 6. Deliver mock SMS
            await sms_provider.send_sms(
                recipient_phone_or_hash=farmer.phone_hash,
                text=localized.sms_text,
                message_type="warning",
            )

            # 7. Create FarmerWarning link
            fw_record = FarmerWarning(
                id=str(uuid.uuid4()),
                warning_id=warning_obj.id,
                farmer_id=farmer.id,
                delivery_status="DELIVERED",
                delivered_at=now,
            )
            session.add(fw_record)

            # 8. Create WebNotification record
            web_notif = WebNotification(
                id=str(uuid.uuid4()),
                farmer_id=farmer.id,
                title=localized.title,
                message=localized.description,
                is_read=False,
                created_at=now,
            )
            session.add(web_notif)

            delivered_count += 1

        await session.commit()

        logger.info(
            f"Warning dispatch for {location_name} complete: "
            f"delivered={delivered_count}, cap_suppressed={cap_suppressed_count}, "
            f"dupe_suppressed={dupe_suppressed_count}"
        )

        return {
            "location": location_name,
            "warning_active": True,
            "severity": classification.severity,
            "warning_id": warning_obj.id,
            "eligible_total": len(eligible_farmers),
            "delivered": delivered_count,
            "cap_suppressed": cap_suppressed_count,
            "dupe_suppressed": dupe_suppressed_count,
        }
