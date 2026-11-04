"""Official heavy-rain categories from the region (IMD in India),
and our own "unusual rain": rain that is rare for this place, judged by its own history.

IMD's mm lines are national. A forecast square is about 25 km wide and its rain is an average,
so it seldom reaches 115.6 mm even when real places in it flood. Comparing each place with its
own wettest days catches rain that is dangerous there."""

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


def rain_climate(daily_mm: list[float], percentile: float, min_mm: float) -> dict:
    """A place's "unusual rain" line from decades of daily rain: the given percentile of all
    days, never below min_mm (so a dry place is not warned for an ordinary shower)."""
    ordered = sorted(daily_mm)
    if not ordered:
        raise ValueError("no rain history")
    line = ordered[min(len(ordered) - 1, int(percentile / 100 * len(ordered)))]
    return {"unusual_mm": round(max(line, min_mm), 1), "percentile": percentile}


def detect_unusual_rain(
    area: Area, rainfall: EnsembleForecast, climate: dict, issue_date: date, rules: dict,
) -> list[HazardDetection]:
    """One detection per day when enough forecast runs reach this place's unusual-rain line."""
    line = climate["unusual_mm"]
    share = share_of_runs_agreeing(rainfall, lambda i, v: v >= line)
    return [
        HazardDetection(
            area_id=area.id,
            hazard=Hazard.UNUSUAL_RAIN,
            severity="unusual",
            first_day=day,
            last_day=day,
            days_ahead=days_ahead(day, issue_date),
            agreement=round(share[i], 2),
            evidence={"rule": "ours (rain rare for this place)", "threshold_mm": line,
                      "percentile": climate["percentile"], "place": area.name},
        )
        for i, day in enumerate(rainfall.dates)
        if share[i] >= rules["min_agreement"]
    ]
