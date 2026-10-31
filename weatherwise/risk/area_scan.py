"""Runs every hazard check for one area: the core of the daily risk scan (plan §5.4)."""

from dataclasses import dataclass, field
from datetime import date
from statistics import median

from weatherwise.risk.dry_spell import detect_dry_spell, detect_sowing_risk
from weatherwise.risk.flood_guide_trigger import FloodGuideDecision, decide_flood_guide_mode
from weatherwise.risk.heat_wave import detect_excess_heat, detect_heat_wave, detect_humid_heat
from weatherwise.risk.heavy_rain import detect_heavy_rain
from weatherwise.risk.models import Area, EnsembleForecast, ForecastDataMissing, Hazard, HazardDetection
from weatherwise.risk.river_flood import detect_river_flood
from weatherwise.rules import in_season


@dataclass(frozen=True)
class AreaWeather:
    """Everything the scan needs for one area, already fetched and parsed."""

    tmax: EnsembleForecast
    feels_like_tmax: EnsembleForecast
    rainfall: EnsembleForecast
    normal_tmax: dict[str, float]  # "MM-DD" -> normal daily max, deg C
    past_dry_days: int
    soil_moisture: float | None
    river_discharge: EnsembleForecast | None = None
    flood_level_m3s: float | None = None
    upstream_rainfall: dict[str, EnsembleForecast] = field(default_factory=dict)
    mean_temp: EnsembleForecast | None = None
    past_30_day_means: list[float] = field(default_factory=list)
    heat_climate: dict | None = None  # Excess Heat Factor baseline for this cell


@dataclass
class ScanResult:
    area: Area
    issue_date: date
    detections: list[HazardDetection] = field(default_factory=list)
    data_missing: list[Hazard] = field(default_factory=list)  # never read as "no risk"
    flood_guide: FloodGuideDecision = field(default_factory=lambda: FloodGuideDecision(None))


def scan_area(
    area: Area,
    weather: AreaWeather,
    issue_date: date,
    rules: dict,
    official_alert: str | None = None,
) -> ScanResult:
    result = ScanResult(area, issue_date)
    seasons = rules["seasons"]
    normal_by_date = {d: weather.normal_tmax[d.strftime("%m-%d")] for d in weather.tmax.dates}
    sowing_now = any(in_season(issue_date, w) for w in seasons["sowing_windows"].values())
    rainfed_season_now = any(
        in_season(issue_date, w) for w in seasons["rainfed_crop_seasons"].values()
    )

    checks = [
        (Hazard.HEAT_WAVE, lambda: detect_heat_wave(
            area, weather.tmax, normal_by_date, issue_date, rules["heat"])),
        (Hazard.HUMID_HEAT, lambda: detect_humid_heat(
            area, weather.feels_like_tmax, issue_date, rules["humid_heat"])),
        (Hazard.HEAVY_RAIN, lambda: detect_heavy_rain(
            area, weather.rainfall, issue_date, rules["heavy_rain"])),
        (Hazard.DRY_SPELL, lambda: detect_dry_spell(
            area, weather.rainfall, issue_date, rules["dry_spell"],
            in_crop_season=rainfed_season_now,
            past_dry_days=weather.past_dry_days, soil_moisture=weather.soil_moisture)),
        (Hazard.SOWING_RISK, lambda: detect_sowing_risk(
            area, weather.rainfall, issue_date, rules["sowing"],
            in_sowing_window=sowing_now, soil_moisture=weather.soil_moisture,
            soil_moisture_dry=rules["dry_spell"]["soil_moisture_dry"])),
    ]
    if weather.mean_temp is not None and weather.heat_climate is not None:
        checks.append((Hazard.EXCESS_HEAT, lambda: detect_excess_heat(
            area, weather.mean_temp, weather.past_30_day_means, weather.heat_climate,
            issue_date, rules["excess_heat"])))
    for place, rainfall in weather.upstream_rainfall.items():
        checks.append((Hazard.HEAVY_RAIN, lambda p=place, r=rainfall: detect_heavy_rain(
            area, r, issue_date, rules["heavy_rain"], place=p)))
    if weather.river_discharge is not None and weather.flood_level_m3s is not None:
        checks.append((Hazard.RIVER_FLOOD, lambda: detect_river_flood(
            area, weather.river_discharge, weather.flood_level_m3s, issue_date,
            rules["river_flood"])))

    for hazard, check in checks:
        try:
            result.detections.extend(check())
        except ForecastDataMissing:
            if hazard not in result.data_missing:
                result.data_missing.append(hazard)

    result.flood_guide = decide_flood_guide_mode(
        result.detections, rules["flood_guide"], official_alert
    )
    return result


def _middle_run(forecast: EnsembleForecast | None, i: int) -> float | None:
    """The middle value across forecast runs for day i (None if no run has a value)."""
    if forecast is None or i >= len(forecast.values):
        return None
    valid = [v for v in forecast.values[i] if v is not None]
    return round(median(valid), 1) if valid else None


def daily_outlook(weather: AreaWeather, detections: list[HazardDetection], days: int = 7) -> list[dict]:
    """One row per forecast day for the website's 7-day strip: middle-run values plus the hazards
    that cover the day. Display only; the warnings themselves come from scan_area."""
    rows = []
    for i, day in enumerate(weather.tmax.dates[:days]):
        rows.append({
            "day": day.isoformat(),
            "tmax_c": _middle_run(weather.tmax, i),
            "normal_tmax_c": weather.normal_tmax.get(day.strftime("%m-%d")),
            "feels_like_max_c": _middle_run(weather.feels_like_tmax, i),
            "rain_mm": _middle_run(weather.rainfall, i),
            "river_m3s": _middle_run(weather.river_discharge, i),
            "hazards": sorted({f"{d.hazard.value}:{d.severity}" for d in detections
                               if d.first_day <= day <= d.last_day}),
        })
    return rows
