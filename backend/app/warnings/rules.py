"""Threshold rules for agricultural heavy-rainfall warnings.

Note: Thresholds are initial engineering placeholders pending local agronomist review.
"""
from dataclasses import dataclass

from app.weather.base import WeatherForecast


@dataclass
class WarningClassification:
    is_active: bool
    severity: str  # 'NONE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    max_daily_rainfall_mm: float
    total_rainfall_mm: float
    affected_date: str | None


class HeavyRainfallRules:
    """Classifies weather forecasts into warning severity levels."""

    # Daily precipitation thresholds (mm in 24 hours)
    THRESHOLD_LOW = 20.0       # Localized ponding, wet soils
    THRESHOLD_MEDIUM = 35.0    # Significant waterlogging risk
    THRESHOLD_HIGH = 50.0      # Flooding and soil erosion danger
    THRESHOLD_CRITICAL = 80.0  # Severe flash flood and crop destruction

    @classmethod
    def evaluate(cls, forecast: WeatherForecast) -> WarningClassification:
        """Evaluate a 3-day weather forecast against rainfall thresholds."""
        max_daily = 0.0
        affected_date = None

        if forecast.daily:
            for d in forecast.daily:
                if d.precipitation_sum_mm > max_daily:
                    max_daily = d.precipitation_sum_mm
                    affected_date = d.date
        else:
            max_daily = forecast.precipitation_sum_mm

        if max_daily >= cls.THRESHOLD_CRITICAL:
            return WarningClassification(
                is_active=True,
                severity="CRITICAL",
                max_daily_rainfall_mm=max_daily,
                total_rainfall_mm=forecast.precipitation_sum_mm,
                affected_date=affected_date,
            )
        elif max_daily >= cls.THRESHOLD_HIGH:
            return WarningClassification(
                is_active=True,
                severity="HIGH",
                max_daily_rainfall_mm=max_daily,
                total_rainfall_mm=forecast.precipitation_sum_mm,
                affected_date=affected_date,
            )
        elif max_daily >= cls.THRESHOLD_MEDIUM:
            return WarningClassification(
                is_active=True,
                severity="MEDIUM",
                max_daily_rainfall_mm=max_daily,
                total_rainfall_mm=forecast.precipitation_sum_mm,
                affected_date=affected_date,
            )
        elif max_daily >= cls.THRESHOLD_LOW:
            return WarningClassification(
                is_active=True,
                severity="LOW",
                max_daily_rainfall_mm=max_daily,
                total_rainfall_mm=forecast.precipitation_sum_mm,
                affected_date=affected_date,
            )
        else:
            return WarningClassification(
                is_active=False,
                severity="NONE",
                max_daily_rainfall_mm=max_daily,
                total_rainfall_mm=forecast.precipitation_sum_mm,
                affected_date=None,
            )
