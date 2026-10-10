"""Abstract interface for Weather providers."""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class DailyForecast(BaseModel):
    date: str
    precipitation_sum_mm: float = 0.0
    precipitation_probability: float = 0.0
    max_temperature_c: float = 20.0
    min_temperature_c: float = 12.0
    wind_speed_max_kmh: float = 10.0
    weather_code: int = 0
    is_rainy: bool = False
    is_heavy_rain: bool = False
    day_offset: int = 0
    temperature_max_c: float = 20.0
    temperature_min_c: float = 12.0


class WeatherForecast(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    precipitation_sum_mm: float
    precipitation_probability: float
    max_temperature_c: float
    min_temperature_c: float
    wind_speed_max_kmh: float = 0.0
    is_heavy_rain: bool = False
    summary: str = ""
    daily: list[DailyForecast] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class BaseWeatherProvider(ABC):
    @abstractmethod
    async def get_forecast(
        self, latitude: float, longitude: float, location_name: str = "Unknown", days: int = 3
    ) -> WeatherForecast:
        """Fetch weather forecast for given geographic coordinates."""
