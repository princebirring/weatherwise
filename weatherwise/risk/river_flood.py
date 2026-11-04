"""River flow forecast above the area's flood level.

This only reports what the river model shows. Whether that means "prepare" or
"urgent" is decided in flood_guide_trigger.py, where model data alone never
reaches urgent.
"""

from datetime import date

from weatherwise.risk.forecast_agreement import days_ahead, share_of_runs_agreeing
from weatherwise.risk.models import Area, EnsembleForecast, Hazard, HazardDetection


def detect_river_flood(
    area: Area,
    river_discharge: EnsembleForecast,
    flood_level_m3s: float,
    issue_date: date,
    rules: dict,
) -> list[HazardDetection]:
    """The first day enough forecast runs agree the river passes its flood level."""
    share = share_of_runs_agreeing(river_discharge, lambda i, v: v >= flood_level_m3s)
    for i, day in enumerate(river_discharge.dates):
        if share[i] < rules["min_agreement"]:
            continue
        return [
            HazardDetection(
                area_id=area.id,
                hazard=Hazard.RIVER_FLOOD,
                severity="above_flood_level",
                first_day=day,
                last_day=day,
                days_ahead=days_ahead(day, issue_date),
                agreement=round(share[i], 2),
                evidence={
                    "flood_level_m3s": flood_level_m3s,
                    "highest_run_m3s": max(v for v in river_discharge.values[i] if v is not None),
                },
            )
        ]
    return []
