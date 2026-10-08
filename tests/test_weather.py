"""Unit tests for Phase 7: Weather integration, location directory, and risk analysis."""
import pytest

from app.pipeline import SessionState, process_utterance
from app.weather.base import DailyForecast, WeatherForecast
from app.weather.location import (
    format_spoken_location_confirmation,
    resolve_location,
)
from app.weather.provider import (
    MockWeatherProvider,
    OpenMeteoWeatherProvider,
)
from app.weather.risk import WeatherRiskAnalyzer


@pytest.mark.asyncio
async def test_mock_weather_provider():
    """Verify mock provider generates deterministic dry and rain forecasts."""
    mock_dry = MockWeatherProvider(simulate_rain=False)
    fc_dry = await mock_dry.get_forecast(8.54, 39.27, "Adama", days=3)
    assert fc_dry.location_name == "Adama"
    assert fc_dry.is_heavy_rain is False
    assert len(fc_dry.daily) == 3

    mock_heavy = MockWeatherProvider(simulate_heavy_rain=True)
    fc_heavy = await mock_heavy.get_forecast(8.54, 39.27, "Adama", days=3)
    assert fc_heavy.is_heavy_rain is True
    assert fc_heavy.precipitation_sum_mm >= 20.0


@pytest.mark.asyncio
async def test_open_meteo_provider_with_cache():
    """Verify Open-Meteo provider retrieves forecast and utilizes cache."""
    provider = OpenMeteoWeatherProvider()
    # Adama coordinates
    forecast = await provider.get_forecast(8.54, 39.27, "Adama", days=3)
    assert forecast.location_name == "Adama"
    assert len(forecast.daily) == 3
    assert forecast.max_temperature_c > 0

    # Call again to test cache hit path
    cached = await provider.get_forecast(8.54, 39.27, "Adama", days=3)
    assert cached.location_name == "Adama"
    assert len(cached.daily) == 3


def test_location_resolution_multilingual():
    """Verify place name fuzzy matching across Amharic, Oromo, and English."""
    # Amharic query
    loc_am = resolve_location("በአዳማ አካባቢ ዝናብ አለ?")
    assert loc_am is not None
    assert loc_am.name == "Adama"
    assert loc_am.region == "Oromia"

    # Alias check (Nazret -> Adama)
    loc_alias = resolve_location("ናዝሬት ላይ መርጨት እፈልጋለሁ")
    assert loc_alias is not None
    assert loc_alias.name == "Adama"

    # Oromo query
    loc_om = resolve_location("Bishooftuu keessatti roobni jiraa?")
    assert loc_om is not None
    assert loc_om.name == "Bishoftu"

    # Unknown location
    loc_none = resolve_location("በማያውቅ ከተማ ውስጥ")
    assert loc_none is None


def test_spoken_location_confirmation():
    """Verify spoken location confirmation phrasing."""
    match = resolve_location("Ambo")
    assert match is not None
    phrase_am = format_spoken_location_confirmation(match, "am")
    assert "በአምቦ አካባቢ" in phrase_am

    phrase_om = format_spoken_location_confirmation(match, "om")
    assert "Naannoo Ambootti" in phrase_om


def test_weather_risk_spraying_evaluation():
    """Verify spraying risk evaluation detects rain and wind hazards."""
    # High rain scenario -> unsafe to spray
    rainy_fc = WeatherForecast(
        location_name="Adama",
        latitude=8.54,
        longitude=39.27,
        precipitation_sum_mm=15.0,
        precipitation_probability=80.0,
        max_temperature_c=22.0,
        min_temperature_c=14.0,
        wind_speed_max_kmh=8.0,
        daily=[
            DailyForecast(
                date="2026-10-10",
                precipitation_sum_mm=10.0,
                precipitation_probability=80.0,
                wind_speed_max_kmh=8.0,
            )
        ],
    )
    risk_rain = WeatherRiskAnalyzer.evaluate_spraying(rainy_fc)
    assert risk_rain.can_spray is False
    assert risk_rain.risk_level == "HIGH"
    assert "ዝናብ" in risk_rain.reason_am
    assert "roob" in risk_rain.reason_om.lower()

    # Dry & calm scenario -> safe to spray
    calm_fc = WeatherForecast(
        location_name="Adama",
        latitude=8.54,
        longitude=39.27,
        precipitation_sum_mm=0.0,
        precipitation_probability=5.0,
        max_temperature_c=24.0,
        min_temperature_c=12.0,
        wind_speed_max_kmh=6.0,
        daily=[
            DailyForecast(
                date="2026-10-10",
                precipitation_sum_mm=0.0,
                precipitation_probability=5.0,
                wind_speed_max_kmh=6.0,
            )
        ],
    )
    risk_calm = WeatherRiskAnalyzer.evaluate_spraying(calm_fc)
    assert risk_calm.can_spray is True
    assert risk_calm.risk_level == "LOW"
    assert "ምቹ" in risk_calm.reason_am


def test_heavy_rainfall_hazard():
    """Verify heavy rainfall warning triggers at >= 20mm."""
    fc_heavy = WeatherForecast(
        location_name="Hawassa",
        latitude=7.05,
        longitude=38.47,
        precipitation_sum_mm=25.0,
        precipitation_probability=90.0,
        max_temperature_c=20.0,
        min_temperature_c=12.0,
        daily=[
            DailyForecast(
                date="2026-10-10",
                precipitation_sum_mm=22.0,
                precipitation_probability=90.0,
            )
        ],
    )
    assert WeatherRiskAnalyzer.is_heavy_rainfall_hazard(fc_heavy) is True


@pytest.mark.asyncio
async def test_pipeline_spraying_query():
    """Verify end-to-end pipeline handles spraying question with location."""
    session = SessionState(
        session_id="call-weather-test-1",
        caller_hash="hash123",
        language="am",
    )
    # Question asks: Can I spray tomorrow in Adama?
    res = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override="ነገ በአዳማ ኬሚካል መርጨት እችላለሁ?",
    )
    assert res.metadata.grounded is True
    assert res.metadata.topic == "weather_spraying"
    assert "አዳማ" in res.text
    assert session.extracted_location == "Adama"


@pytest.mark.asyncio
async def test_pipeline_weather_missing_location():
    """Verify pipeline asks for location when caller asks about weather without specifying place."""
    session = SessionState(
        session_id="call-weather-test-2",
        caller_hash="hash456",
        language="am",
    )
    res = await process_utterance(
        audio_bytes=None,
        session=session,
        text_override="ነገ ዝናብ ይዘንባል?",
    )
    assert res.metadata.topic == "weather_location_request"
    assert "ወረዳ" in res.text or "አካባቢ" in res.text
