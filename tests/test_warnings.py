"""Unit tests for Phase 10: Heavy-rainfall warning rules, targeting, and follow-up loop."""
import uuid
from datetime import datetime

import pytest

from app.database.models import Farmer, FarmerContext
from app.database.session import async_session_factory
from app.warnings.followup import explain_warning_to_caller, get_latest_farmer_warning
from app.warnings.generate import generate_rainfall_warning_content
from app.warnings.rules import HeavyRainfallRules
from app.warnings.targeting import WarningTargetingEngine
from app.weather.base import DailyForecast, WeatherForecast


def test_heavy_rainfall_rules_classification():
    """Verify rainfall thresholds map to correct severity levels."""
    # Under 20mm -> NONE
    fc_none = WeatherForecast(
        location_name="Test",
        latitude=8.5,
        longitude=39.2,
        precipitation_sum_mm=12.0,
        precipitation_probability=50.0,
        max_temperature_c=22.0,
        min_temperature_c=12.0,
        daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=12.0)],
    )
    assert HeavyRainfallRules.evaluate(fc_none).severity == "NONE"

    # 25mm -> LOW
    fc_low = WeatherForecast(
        location_name="Test",
        latitude=8.5,
        longitude=39.2,
        precipitation_sum_mm=25.0,
        precipitation_probability=70.0,
        max_temperature_c=22.0,
        min_temperature_c=12.0,
        daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=25.0)],
    )
    assert HeavyRainfallRules.evaluate(fc_low).severity == "LOW"

    # 45mm -> MEDIUM
    fc_med = WeatherForecast(
        location_name="Test",
        latitude=8.5,
        longitude=39.2,
        precipitation_sum_mm=45.0,
        precipitation_probability=85.0,
        max_temperature_c=22.0,
        min_temperature_c=12.0,
        daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=45.0)],
    )
    assert HeavyRainfallRules.evaluate(fc_med).severity == "MEDIUM"

    # 65mm -> HIGH
    fc_high = WeatherForecast(
        location_name="Test",
        latitude=8.5,
        longitude=39.2,
        precipitation_sum_mm=65.0,
        precipitation_probability=95.0,
        max_temperature_c=22.0,
        min_temperature_c=12.0,
        daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=65.0)],
    )
    assert HeavyRainfallRules.evaluate(fc_high).severity == "HIGH"

    # 85mm -> CRITICAL
    fc_crit = WeatherForecast(
        location_name="Test",
        latitude=8.5,
        longitude=39.2,
        precipitation_sum_mm=85.0,
        precipitation_probability=99.0,
        max_temperature_c=22.0,
        min_temperature_c=12.0,
        daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=85.0)],
    )
    assert HeavyRainfallRules.evaluate(fc_crit).severity == "CRITICAL"


def test_localized_warning_content():
    """Verify generated warning text contains actionable advice in both languages."""
    content_am = generate_rainfall_warning_content("አዳማ", "HIGH", 55.0, "am")
    assert "ማስጠንቀቂያ" in content_am.title
    assert "ቦይ" in content_am.description
    assert "ሄሎ ፋርመር፡" in content_am.sms_text

    content_om = generate_rainfall_warning_content("Adaamaa", "HIGH", 55.0, "om")
    assert "Akeekkachiisa" in content_om.title
    assert "bo'oo lolaa" in content_om.description
    assert "Heelo Faarmar:" in content_om.sms_text


@pytest.mark.asyncio
async def test_targeting_engine_opt_in_and_dispatch():
    """Verify targeting engine targets only opted-in farmers and respects daily caps."""
    test_woreda = f"TestWoreda_{uuid.uuid4().hex[:6]}"
    phone_hash_opted = f"opted_{uuid.uuid4().hex[:12]}"
    phone_hash_unopted = f"unopted_{uuid.uuid4().hex[:12]}"

    async with async_session_factory() as session:
        # Create opted-in farmer
        f_opt = Farmer(
            id=str(uuid.uuid4()),
            phone_hash=phone_hash_opted,
            is_opted_in_warnings=True,
            preferred_language="am",
            created_at=datetime.utcnow(),
        )
        session.add(f_opt)
        c_opt = FarmerContext(
            id=str(uuid.uuid4()),
            farmer_id=f_opt.id,
            woreda=test_woreda,
            region="Oromia",
        )
        session.add(c_opt)

        # Create un-opted farmer in same woreda
        f_unopt = Farmer(
            id=str(uuid.uuid4()),
            phone_hash=phone_hash_unopted,
            is_opted_in_warnings=False,
            preferred_language="am",
            created_at=datetime.utcnow(),
        )
        session.add(f_unopt)
        c_unopt = FarmerContext(
            id=str(uuid.uuid4()),
            farmer_id=f_unopt.id,
            woreda=test_woreda,
            region="Oromia",
        )
        session.add(c_unopt)
        await session.commit()

        # Run targeting dispatch
        fc = WeatherForecast(
            location_name=test_woreda,
            latitude=8.5,
            longitude=39.2,
            precipitation_sum_mm=40.0,
            precipitation_probability=90.0,
            max_temperature_c=22.0,
            min_temperature_c=12.0,
            daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=40.0)],
        )

        # 1st dispatch: only opted-in farmer receives warning
        run1 = await WarningTargetingEngine.process_location_warning(
            location_name=test_woreda,
            forecast=fc,
            session=session,
        )
        assert run1["warning_active"] is True
        assert run1["eligible_total"] == 1
        assert run1["delivered"] == 1

        # 2nd dispatch: daily cap / duplicate suppression suppresses warning
        run2 = await WarningTargetingEngine.process_location_warning(
            location_name=test_woreda,
            forecast=fc,
            session=session,
        )
        assert run2["delivered"] == 0
        assert (run2["dupe_suppressed"] + run2["cap_suppressed"]) >= 1


@pytest.mark.asyncio
async def test_warning_followup_loop():
    """Verify follow-up loop finds latest warning for farmer and explains it."""
    test_woreda = f"FollowupWoreda_{uuid.uuid4().hex[:6]}"
    phone_hash = f"caller_{uuid.uuid4().hex[:12]}"

    async with async_session_factory() as session:
        farmer = Farmer(
            id=str(uuid.uuid4()),
            phone_hash=phone_hash,
            is_opted_in_warnings=True,
            preferred_language="am",
            created_at=datetime.utcnow(),
        )
        session.add(farmer)
        ctx = FarmerContext(
            id=str(uuid.uuid4()),
            farmer_id=farmer.id,
            woreda=test_woreda,
            region="Oromia",
        )
        session.add(ctx)
        await session.commit()

        fc = WeatherForecast(
            location_name=test_woreda,
            latitude=8.5,
            longitude=39.2,
            precipitation_sum_mm=55.0,
            precipitation_probability=90.0,
            max_temperature_c=22.0,
            min_temperature_c=12.0,
            daily=[DailyForecast(date="2026-10-15", precipitation_sum_mm=55.0)],
        )
        await WarningTargetingEngine.process_location_warning(test_woreda, fc, session)

        # Retrieve latest warning for farmer
        warning = await get_latest_farmer_warning(phone_hash, session)
        assert warning is not None
        assert warning.severity == "HIGH"

        # Check spoken explanations
        explanation_am = explain_warning_to_caller(warning, language="am")
        assert "ማስጠንቀቂያ" in explanation_am
        assert test_woreda in explanation_am

        explanation_om = explain_warning_to_caller(warning, language="om")
        assert "akeekkachiisni" in explanation_om
        assert test_woreda in explanation_om
