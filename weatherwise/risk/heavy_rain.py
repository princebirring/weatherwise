"""Flow 4 trigger: official heavy-rain categories from the region (IMD in India; plan §5.2)."""

from datetime import date

from weatherwise.risk.forecast_agreement import days_ahead, share_of_runs_agreeing
from weatherwise.risk.models import Area, EnsembleForecast, Hazard, HazardDetection

CATEGORIES = ("extremely_heavy", "very_heavy", "heavy")  # highest first


def detect_heavy_rain(
    area: Area,
    rainfall: EnsembleForecast,
    issue_date: date,
    rules: dict,
    place: str | None = None,
) -> list[HazardDetection]:
    """One detection per day: the highest category enough forecast runs agree on.

    place names where the rain falls: the area itself (default) or an upstream point.
    """
    shares = {
        category: share_of_runs_agreeing(rainfall, lambda i, v, mm=rules[category]: v >= mm)
        for category in CATEGORIES
    }

    detections = []
    for i, day in enumerate(rainfall.dates):
        for category in CATEGORIES:
            if shares[category][i] >= rules["min_agreement"]:
                detections.append(
                    HazardDetection(
                        area_id=area.id,
                        hazard=Hazard.HEAVY_RAIN,
                        severity=category,
                        first_day=day,
                        last_day=day,
                        days_ahead=days_ahead(day, issue_date),
                        agreement=round(shares[category][i], 2),
                        evidence={"threshold_mm": rules[category], "place": place or area.name},
                    )
                )
                break
    return detections
