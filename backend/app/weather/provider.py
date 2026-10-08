"""Weather provider implementations: Open-Meteo and Mock fallback."""
import logging
import time
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.config import settings
from app.weather.base import BaseWeatherProvider, DailyForecast, WeatherForecast

logger = logging.getLogger(__name__)

# In-memory backup cache: {key: (timestamp, forecast_dict)}
_MEMORY_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 3600  # 60 minutes cache


class MockWeatherProvider(BaseWeatherProvider):
    """Deterministic mock provider for testing and offline scenarios."""

    def __init__(self, simulate_rain: bool = False, simulate_heavy_rain: bool = False):
        self.simulate_rain = simulate_rain
        self.simulate_heavy_rain = simulate_heavy_rain

    async def get_forecast(
        self, latitude: float, longitude: float, location_name: str = "Adama", days: int = 3
    ) -> WeatherForecast:
        precip = 25.0 if self.simulate_heavy_rain else (5.0 if self.simulate_rain else 0.0)
        prob = 85.0 if (self.simulate_rain or self.simulate_heavy_rain) else 10.0
        wind = 22.0 if self.simulate_heavy_rain else 8.0

        daily_list = []
        for i in range(days):
            daily_list.append(
                DailyForecast(
                    date=f"2026-10-{10+i:02d}",
                    precipitation_sum_mm=precip,
                    precipitation_probability=prob,
                    max_temperature_c=24.0,
                    min_temperature_c=13.0,
                    wind_speed_max_kmh=wind,
                    weather_code=65 if precip > 10 else (51 if precip > 0 else 0),
                    is_rainy=precip > 1.0,
                    is_heavy_rain=precip >= 20.0,
                )
            )

        summary = (
            f"Heavy rainfall forecast ({precip:.1f} mm) in {location_name}"
            if self.simulate_heavy_rain
            else (
                f"Rain expected ({precip:.1f} mm) in {location_name}"
                if self.simulate_rain
                else f"Dry and clear conditions in {location_name}"
            )
        )

        return WeatherForecast(
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            precipitation_sum_mm=precip * days,
            precipitation_probability=prob,
            max_temperature_c=24.0,
            min_temperature_c=13.0,
            wind_speed_max_kmh=wind,
            is_heavy_rain=self.simulate_heavy_rain,
            summary=summary,
            daily=daily_list,
        )


class OpenMeteoWeatherProvider(BaseWeatherProvider):
    """Open-Meteo free API weather provider with Redis/Memory caching."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: aioredis.Redis | None = None
        self._fallback_mock = MockWeatherProvider()

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                await self._redis.ping()
            except Exception as e:
                logger.debug(f"Redis not available for weather caching: {e}")
                self._redis = None
        return self._redis

    async def _get_from_cache(self, cache_key: str) -> WeatherForecast | None:
        # 1. Try Redis
        try:
            r = await self._get_redis()
            if r:
                data_str = await r.get(cache_key)
                if data_str:
                    logger.debug(f"Weather cache hit in Redis for {cache_key}")
                    return WeatherForecast.model_validate_json(data_str)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

        # 2. Try in-memory backup cache
        if cache_key in _MEMORY_CACHE:
            ts, forecast_dict = _MEMORY_CACHE[cache_key]
            if time.time() - ts < CACHE_TTL_SECONDS:
                logger.debug(f"Weather cache hit in memory for {cache_key}")
                return WeatherForecast(**forecast_dict)
            else:
                del _MEMORY_CACHE[cache_key]

        return None

    async def _set_to_cache(self, cache_key: str, forecast: WeatherForecast) -> None:
        forecast_json = forecast.model_dump_json()
        try:
            r = await self._get_redis()
            if r:
                await r.setex(cache_key, CACHE_TTL_SECONDS, forecast_json)
        except Exception as e:
            logger.debug(f"Redis cache write error: {e}")

        _MEMORY_CACHE[cache_key] = (time.time(), forecast.model_dump())

    async def get_forecast(
        self, latitude: float, longitude: float, location_name: str = "Unknown", days: int = 3
    ) -> WeatherForecast:
        # Cache key rounded to 2 decimal places (~1.1km grid)
        cache_key = f"weather:{round(latitude, 2)}:{round(longitude, 2)}:{days}"

        cached = await self._get_from_cache(cache_key)
        if cached:
            cached.location_name = location_name
            return cached

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "daily": (
                "weathercode,temperature_2m_max,temperature_2m_min,"
                "precipitation_sum,precipitation_probability_max,windspeed_10m_max"
            ),
            "timezone": "Africa/Addis_Ababa",
            "forecast_days": days,
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            daily_raw = data.get("daily", {})
            dates = daily_raw.get("time", [])
            precip_sums = daily_raw.get("precipitation_sum", [0.0] * days)
            precip_probs = daily_raw.get("precipitation_probability_max", [0.0] * days)
            temp_maxes = daily_raw.get("temperature_2m_max", [20.0] * days)
            temp_mins = daily_raw.get("temperature_2m_min", [12.0] * days)
            winds = daily_raw.get("windspeed_10m_max", [10.0] * days)
            weather_codes = daily_raw.get("weathercode", [0] * days)

            daily_list: list[DailyForecast] = []
            total_precip = 0.0
            max_prob = 0.0
            is_heavy = False

            for i in range(len(dates)):
                p_sum = float(precip_sums[i] or 0.0)
                p_prob = float(precip_probs[i] or 0.0)
                w_max = float(winds[i] or 0.0)
                heavy = p_sum >= 20.0
                if heavy:
                    is_heavy = True

                total_precip += p_sum
                if p_prob > max_prob:
                    max_prob = p_prob

                daily_list.append(
                    DailyForecast(
                        date=dates[i],
                        precipitation_sum_mm=p_sum,
                        precipitation_probability=p_prob,
                        max_temperature_c=float(temp_maxes[i] or 20.0),
                        min_temperature_c=float(temp_mins[i] or 12.0),
                        wind_speed_max_kmh=w_max,
                        weather_code=int(weather_codes[i] or 0),
                        is_rainy=p_sum > 1.0,
                        is_heavy_rain=heavy,
                    )
                )

            summary = (
                f"Heavy rain expected ({total_precip:.1f} mm over {days} days)"
                if is_heavy
                else (
                    f"Rain possible ({total_precip:.1f} mm, {max_prob:.0f}% chance)"
                    if total_precip > 2.0
                    else "Fair weather and dry conditions"
                )
            )

            forecast = WeatherForecast(
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                precipitation_sum_mm=total_precip,
                precipitation_probability=max_prob,
                max_temperature_c=max(temp_maxes) if temp_maxes else 20.0,
                min_temperature_c=min(temp_mins) if temp_mins else 12.0,
                wind_speed_max_kmh=max(winds) if winds else 10.0,
                is_heavy_rain=is_heavy,
                summary=summary,
                daily=daily_list,
                raw_data=data,
            )

            await self._set_to_cache(cache_key, forecast)
            return forecast

        except Exception as exc:
            logger.warning(
                f"OpenMeteo API call failed ({exc}); falling back to mock provider for {location_name}"
            )
            return await self._fallback_mock.get_forecast(
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
                days=days,
            )


def get_weather_provider(provider_type: str | None = None) -> BaseWeatherProvider:
    """Factory to get the configured weather provider."""
    ptype = provider_type or getattr(settings, "WEATHER_PROVIDER", "open_meteo")
    if ptype == "mock":
        return MockWeatherProvider()
    return OpenMeteoWeatherProvider()
