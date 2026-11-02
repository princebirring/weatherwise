"""Runs every hazard check for one area: the core of the daily risk scan (plan §5.4).

CHECKS names every check. Which ones run is set in the rules ([checks] enabled), so a check can
be switched off for every country, or for one, without touching code. Live scans and replays
both go through run_checks, so a switch or a rule change means the same thing in both.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from statistics import median

from weatherwise.risk.dry_spell import detect_dry_spell, detect_sowing_risk
from weatherwise.risk.flood_guide_trigger import FloodGuideDecision, decide_flood_guide_mode
from weatherwise.risk.heat_wave import detect_excess_heat, detect_heat_wave, detect_work_heat
from weatherwise.risk.heavy_rain import detect_heavy_rain, detect_unusual_rain
from weatherwise.risk.models import Area, EnsembleForecast, ForecastDataMissing, Hazard, HazardDetection
from weatherwise.risk.river_flood import detect_river_flood
from weatherwise.rules import in_season


@dataclass(frozen=True)
class AreaWeather:
    """Everything the scan needs for one area, already fetched, parsed and corrected.
    A check whose inputs are None does not run (replays have no soil moisture, for example)."""

    tmax: EnsembleForecast | None
    feels_like_tmax: EnsembleForecast | None
    rainfall: EnsembleForecast | None
    normal_tmax: dict[str, float]  # "MM-DD" -> normal daily max, deg C
    past_dry_days: int | None = None
    soil_moisture: float | None = None
    river_discharge: EnsembleForecast | None = None
    flood_level_m3s: float | None = None
    upstream_rainfall: dict[str, EnsembleForecast] = field(default_factory=dict)
    mean_temp: EnsembleForecast | None = None
    past_30_day_means: list[float] = field(default_factory=list)
    heat_climate: dict | None = None  # Excess Heat Factor baseline for this cell
    rain_climate: dict | None = None  # this cell's unusual-rain line
    correction: dict = field(default_factory=dict)  # Correction.summary(): what was shifted


@dataclass
class ScanResult:
    area: Area
    issue_date: date
    detections: list[HazardDetection] = field(default_factory=list)
    data_missing: list[Hazard] = field(default_factory=list)  # never read as "no risk"
    flood_guide: FloodGuideDecision = field(default_factory=lambda: FloodGuideDecision(None))


Thunk = Callable[[], list[HazardDetection]]


def _heat_wave(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    if w.tmax is None:
        return []
    normal_by_date = {d: w.normal_tmax[d.strftime("%m-%d")] for d in w.tmax.dates}
    return [lambda: detect_heat_wave(area, w.tmax, normal_by_date, day, rules["heat"])]


def _work_heat(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    if w.feels_like_tmax is None:
        return []
    return [lambda: detect_work_heat(area, w.feels_like_tmax, day, rules["work_heat"])]


def _excess_heat(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    if w.mean_temp is None or w.heat_climate is None:
        return []
    return [lambda: detect_excess_heat(area, w.mean_temp, w.past_30_day_means, w.heat_climate,
                                       day, rules["excess_heat"])]


def _heavy_rain(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    """The area itself and each upstream rain point, each judged on its own."""
    places = ([(None, w.rainfall)] if w.rainfall is not None else []) + list(w.upstream_rainfall.items())
    return [lambda p=p, r=r: detect_heavy_rain(area, r, day, rules["heavy_rain"], place=p)
            for p, r in places]


def _unusual_rain(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    """The area only: upstream points would each need their own rain history."""
    if w.rainfall is None or w.rain_climate is None:
        return []
    return [lambda: detect_unusual_rain(area, w.rainfall, w.rain_climate, day, rules["unusual_rain"])]


def _dry_spell(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    if w.rainfall is None or w.past_dry_days is None:
        return []
    in_season_now = any(in_season(day, s) for s in rules["seasons"]["rainfed_crop_seasons"].values())
    return [lambda: detect_dry_spell(area, w.rainfall, day, rules["dry_spell"], in_crop_season=in_season_now,
                                     past_dry_days=w.past_dry_days, soil_moisture=w.soil_moisture)]


def _sowing_risk(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    if w.rainfall is None or w.past_dry_days is None:
        return []
    sowing_now = any(in_season(day, s) for s in rules["seasons"]["sowing_windows"].values())
    return [lambda: detect_sowing_risk(area, w.rainfall, day, rules["sowing"], in_sowing_window=sowing_now,
                                       soil_moisture=w.soil_moisture,
                                       soil_moisture_dry=rules["dry_spell"]["soil_moisture_dry"])]


def _river_flood(area: Area, w: AreaWeather, day: date, rules: dict) -> list[Thunk]:
    if w.river_discharge is None or w.flood_level_m3s is None:
        return []
    return [lambda: detect_river_flood(area, w.river_discharge, w.flood_level_m3s, day, rules["river_flood"])]


# Every check, by the name used in [checks] enabled: (hazard it reports, what to run).
CHECKS: dict[str, tuple[Hazard, Callable[[Area, AreaWeather, date, dict], list[Thunk]]]] = {
    "heat_wave": (Hazard.HEAT_WAVE, _heat_wave),
    "work_heat": (Hazard.WORK_HEAT, _work_heat),
    "excess_heat": (Hazard.EXCESS_HEAT, _excess_heat),
    "heavy_rain": (Hazard.HEAVY_RAIN, _heavy_rain),
    "unusual_rain": (Hazard.UNUSUAL_RAIN, _unusual_rain),
    "dry_spell": (Hazard.DRY_SPELL, _dry_spell),
    "sowing_risk": (Hazard.SOWING_RISK, _sowing_risk),
    "river_flood": (Hazard.RIVER_FLOOD, _river_flood),
}


def run_checks(area: Area, weather: AreaWeather, issue_date: date, rules: dict,
               result: ScanResult | None = None) -> ScanResult:
    """Every enabled check whose inputs are present. Missing forecast data is recorded, never
    read as "no risk"."""
    result = result or ScanResult(area, issue_date)
    for name in rules["checks"]["enabled"]:
        hazard, parts = CHECKS[name]
        for check in parts(area, weather, issue_date, rules):
            try:
                result.detections.extend(check())
            except ForecastDataMissing:
                if hazard not in result.data_missing:
                    result.data_missing.append(hazard)
    return result


def scan_area(
    area: Area,
    weather: AreaWeather,
    issue_date: date,
    rules: dict,
    official_alert: str | None = None,
) -> ScanResult:
    result = run_checks(area, weather, issue_date, rules)
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


def daily_outlook(weather: AreaWeather, detections: list[HazardDetection], days: int = 7,
                  rainy_day_mm: float | None = None) -> list[dict]:
    """One row per forecast day for the website's 7-day strip: middle-run values plus the hazards
    that cover the day. Display only; the warnings themselves come from scan_area.
    rainy_day is the country's "rainy day" line (IMD: 2.5 mm), so farmers can pick dry days to spray."""
    rows = []
    for i, day in enumerate(weather.tmax.dates[:days]):
        rain = _middle_run(weather.rainfall, i)
        rows.append({
            "day": day.isoformat(),
            "tmax_c": _middle_run(weather.tmax, i),
            "normal_tmax_c": weather.normal_tmax.get(day.strftime("%m-%d")),
            "feels_like_max_c": _middle_run(weather.feels_like_tmax, i),
            "rain_mm": rain,
            "rainy_day": None if rain is None or rainy_day_mm is None else rain >= rainy_day_mm,
            "river_m3s": _middle_run(weather.river_discharge, i),
            "hazards": sorted({f"{d.hazard.value}:{d.severity}" for d in detections
                               if d.first_day <= day <= d.last_day}),
        })
    return rows
