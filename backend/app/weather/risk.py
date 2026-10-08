"""Agricultural weather risk analysis: spraying suitability, planting moisture, and heavy rainfall."""
from dataclasses import dataclass

from app.weather.base import WeatherForecast


@dataclass
class SprayRiskEvaluation:
    can_spray: bool
    risk_level: str  # LOW, MODERATE, HIGH
    reason_en: str
    reason_am: str
    reason_om: str
    rainfall_mm: float
    wind_speed_kmh: float


@dataclass
class PlantingMoistureEvaluation:
    is_suitable: bool
    moisture_status: str  # DRY, OPTIMAL, EXCESSIVE
    summary_am: str
    summary_om: str
    rainfall_mm: float


class WeatherRiskAnalyzer:
    """Analyzes weather forecasts against agricultural operational rules."""

    # Spraying criteria:
    # High risk if expected 24h-48h rain > 1.5mm or rain prob > 40%, or wind > 15 km/h
    # Wind drift damages adjacent crops / reduces efficacy. Rain washes active ingredients.
    MAX_SPRAY_RAIN_MM = 1.5
    MAX_SPRAY_RAIN_PROB = 40.0
    MAX_SPRAY_WIND_KMH = 15.0

    # Heavy rainfall warning threshold (configurable, default 20mm in 24h)
    HEAVY_RAIN_THRESHOLD_MM = 20.0

    @classmethod
    def evaluate_spraying(cls, forecast: WeatherForecast, target_day_idx: int = 0) -> SprayRiskEvaluation:
        """Evaluate if weather conditions allow safe chemical or pesticide spraying."""
        if forecast.daily and target_day_idx < len(forecast.daily):
            day = forecast.daily[target_day_idx]
            rain_mm = day.precipitation_sum_mm
            rain_prob = day.precipitation_probability
            wind_kmh = day.wind_speed_max_kmh
        else:
            rain_mm = forecast.precipitation_sum_mm
            rain_prob = forecast.precipitation_probability
            wind_kmh = forecast.wind_speed_max_kmh

        # Rain risk
        rain_danger = rain_mm >= cls.MAX_SPRAY_RAIN_MM or rain_prob >= cls.MAX_SPRAY_RAIN_PROB
        # Wind risk
        wind_danger = wind_kmh >= cls.MAX_SPRAY_WIND_KMH

        if rain_danger and wind_danger:
            return SprayRiskEvaluation(
                can_spray=False,
                risk_level="HIGH",
                reason_en=f"High risk of rain ({rain_mm:.1f} mm) and strong wind ({wind_kmh:.1f} km/h). Spraying is not recommended.",
                reason_am="ዝናብ ስለሚጠበቅና ኃይለኛ ነፋስ ስላለ ኬሚካል መርጨት አይመከርም። መድኃኒቱ ሊታጠብና በነፋስ ሊበተን ይችላል።",
                reason_om="Roobni waan eegamuufi bubbee cimaa waan jiruuf qoricha biifuun hin gorfamu. Qorichi dhiqamuu fi bubbeen faca'uu danda'a.",
                rainfall_mm=rain_mm,
                wind_speed_kmh=wind_kmh,
            )
        elif rain_danger:
            return SprayRiskEvaluation(
                can_spray=False,
                risk_level="HIGH",
                reason_en=f"Rain is expected ({rain_mm:.1f} mm, {rain_prob:.0f}% chance). Rain will wash away the applied chemicals.",
                reason_am="ዝናብ ስለሚጠበቅ ኬሚካል መርጨት አይመከርም። ዝናቡ ኬሚካሉን አጥቦ ውጤታማነቱን ያሳጣዋል።",
                reason_om="Roobni waan eegamuuf qoricha biifuun hin gorfamu. Roobichi qoricha dhiqee gatii dhabsiisa.",
                rainfall_mm=rain_mm,
                wind_speed_kmh=wind_kmh,
            )
        elif wind_danger:
            return SprayRiskEvaluation(
                can_spray=False,
                risk_level="MODERATE",
                reason_en=f"Strong wind is expected ({wind_kmh:.1f} km/h). Wind drift reduces coverage and endangers other plants.",
                reason_am="ከፍተኛ ነፋስ ስላለ ኬሚካል መርጨት አይመከርም። ነፋሱ መድኃኒቱን ወደ ሌሎች ሰብሎች ሊበትነው ይችላል።",
                reason_om="Bubbee cimaan waan jiruuf qoricha biifuun hin gorfamu. Bubbeen qoricha gara biqiloota birootti facaasa.",
                rainfall_mm=rain_mm,
                wind_speed_kmh=wind_kmh,
            )
        else:
            return SprayRiskEvaluation(
                can_spray=True,
                risk_level="LOW",
                reason_en=f"Weather conditions are calm and dry ({rain_mm:.1f} mm rain, {wind_kmh:.1f} km/h wind). Favorable for spraying.",
                reason_am="የአየር ሁኔታው የተረጋጋና ዝናብ የሌለበት ስለሆነ ኬሚካል ለመርጨት ምቹ ነው። አስፈላጊውን የደህንነት ጥንቃቄ ያድርጉ።",
                reason_om="Haalli qilleensaa kan qabbanaa'ee fi rooba kan hin qabne waan ta'eef qoricha biifuuf mijataadha. Eeggannoo barbaachisaa godhaa.",
                rainfall_mm=rain_mm,
                wind_speed_kmh=wind_kmh,
            )

    @classmethod
    def evaluate_planting(cls, forecast: WeatherForecast) -> PlantingMoistureEvaluation:
        """Evaluate if soil moisture and rainfall forecast are suitable for sowing."""
        total_rain = forecast.precipitation_sum_mm

        if total_rain < 2.0:
            return PlantingMoistureEvaluation(
                is_suitable=False,
                moisture_status="DRY",
                summary_am="በቂ ዝናብ ስለሌለ አፈሩ ደረቅ ሊሆን ይችላል። ዘር ከመዝራትዎ በፊት ተጨማሪ ዝናብ ወይም እርጥበት ይጠብቁ።",
                summary_om="Roobni gahaan waan hin jirreef biyyoon gogaa ta'uu danda'a. Sanyiin osoo hin facaasin dura rooba eegaa.",
                rainfall_mm=total_rain,
            )
        elif total_rain > 40.0:
            return PlantingMoistureEvaluation(
                is_suitable=False,
                moisture_status="EXCESSIVE",
                summary_am="ከፍተኛ ዝናብ ስለሚጠበቅ የውሃ መተኛት ሊፈጠር ይችላል። ዘር እንዳይበሰብስ ጥንቃቄ ያድርጉ።",
                summary_om="Roobni cimaan waan eegamuuf lolaa uumuu danda'a. Sanyiin akka hin tortorreef eeggannoo godhaa.",
                rainfall_mm=total_rain,
            )
        else:
            return PlantingMoistureEvaluation(
                is_suitable=True,
                moisture_status="OPTIMAL",
                summary_am="ተስማሚ እርጥበት የሚሰጥ ዝናብ ይጠበቃል። አፈሩ ለእርሻና ለዘር አመቺ ሁኔታ ላይ ነው።",
                summary_om="Roobni jiidhina gaarii kennu ni eegama. Biyyoon qonnaaf fi sanyii facaasuuf mijataadha.",
                rainfall_mm=total_rain,
            )

    @classmethod
    def is_heavy_rainfall_hazard(cls, forecast: WeatherForecast) -> bool:
        """Check if any forecast day exceeds heavy rainfall threshold (>20mm)."""
        if forecast.daily:
            return any(d.precipitation_sum_mm >= cls.HEAVY_RAIN_THRESHOLD_MM for d in forecast.daily)
        return forecast.precipitation_sum_mm >= cls.HEAVY_RAIN_THRESHOLD_MM
