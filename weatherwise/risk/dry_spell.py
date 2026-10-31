"""Flow 2 triggers: dry spell in the crop season, and the sowing-time rule (plan §5.2)."""

from datetime import date

from weatherwise.risk.forecast_agreement import MIN_FORECAST_RUNS
from weatherwise.risk.models import (
    Area,
    EnsembleForecast,
    ForecastDataMissing,
    Hazard,
    HazardDetection,
)


def _complete_runs(forecast: EnsembleForecast) -> list[list[float]]:
    """Each forecast run as a list of daily values. Runs with any missing day are dropped."""
    n_runs = len(forecast.values[0]) if forecast.values else 0
    complete = []
    for r in range(n_runs):
        days = [forecast.values[d][r] for d in range(len(forecast.dates))]
        if all(v is not None for v in days):
            complete.append(days)
    if len(complete) < MIN_FORECAST_RUNS:
        raise ForecastDataMissing(f"only {len(complete)} complete forecast runs")
    return complete


def _longest_dry_stretch(daily_mm: list[float], past_dry_days: int, dry_day_max_mm: float) -> int:
    """Longest stretch of dry days.

    The current spell (past_dry_days) joins the forecast only if the first forecast
    day is also dry; rain on day one ends it.
    """
    best, current, at_start = 0, 0, True
    for mm in daily_mm:
        if mm < dry_day_max_mm:
            current += 1
        else:
            if at_start and current > 0:
                current += past_dry_days
            at_start = False
            best = max(best, current)
            current = 0
    if at_start and current > 0:
        current += past_dry_days
    return max(best, current)


def detect_dry_spell(
    area: Area,
    rainfall: EnsembleForecast,
    issue_date: date,
    rules: dict,
    *,
    in_crop_season: bool,
    past_dry_days: int = 0,
    soil_moisture: float | None = None,
) -> list[HazardDetection]:
    """A long dry spell that enough forecast runs agree on, with low soil moisture."""
    if not in_crop_season:
        return []
    if soil_moisture is not None and soil_moisture > rules["soil_moisture_dry"]:
        return []

    stretches = [
        _longest_dry_stretch(run, past_dry_days, rules["dry_day_max_mm"])
        for run in _complete_runs(rainfall)
    ]
    share = sum(1 for n in stretches if n >= rules["min_dry_days"]) / len(stretches)
    if share < rules["min_agreement"]:
        return []
    return [
        HazardDetection(
            area_id=area.id,
            hazard=Hazard.DRY_SPELL,
            severity="dry_spell",
            first_day=rainfall.dates[0],
            last_day=rainfall.dates[-1],
            days_ahead=0,
            agreement=round(share, 2),
            evidence={
                "past_dry_days": past_dry_days,
                "median_dry_stretch_days": sorted(stretches)[len(stretches) // 2],
                "soil_moisture": soil_moisture,
            },
        )
    ]


def detect_sowing_risk(
    area: Area,
    rainfall: EnsembleForecast,
    issue_date: date,
    rules: dict,
    *,
    in_sowing_window: bool,
    soil_moisture: float | None,
    soil_moisture_dry: float,
) -> list[HazardDetection]:
    """At sowing time: dry soil and almost no rain in the 2-week forecast."""
    if not in_sowing_window or soil_moisture is None or soil_moisture > soil_moisture_dry:
        return []
    window = rules["forecast_days"]
    totals = [sum(run[:window]) for run in _complete_runs(rainfall)]
    share = sum(1 for mm in totals if mm <= rules["max_total_rain_mm"]) / len(totals)
    if share < rules["min_agreement"]:
        return []
    return [
        HazardDetection(
            area_id=area.id,
            hazard=Hazard.SOWING_RISK,
            severity="sow_or_wait",
            first_day=rainfall.dates[0],
            last_day=rainfall.dates[min(window, len(rainfall.dates)) - 1],
            days_ahead=0,
            agreement=round(share, 2),
            evidence={
                "median_total_rain_mm": round(sorted(totals)[len(totals) // 2], 1),
                "soil_moisture": soil_moisture,
            },
        )
    ]
