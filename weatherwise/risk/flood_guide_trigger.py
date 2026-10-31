"""Decides whether the flood guide starts in prepare or urgent mode (plan §4.3, §5.2, §6.1).

Safety rule: our own model data (river forecast, heavy rain) only ever starts PREPARE.
URGENT ("move now") needs an official red alert, or extremely heavy rain in the area or
upstream within urgent_within_days. We never tell a family to move on our model alone.
"""

from dataclasses import dataclass, field
from datetime import date

from weatherwise.risk.models import Hazard, HazardDetection

PREPARE, URGENT = "prepare", "urgent"


@dataclass(frozen=True)
class FloodGuideDecision:
    mode: str | None  # None, PREPARE, or URGENT
    reasons: list[str] = field(default_factory=list)


def _describe(d: HazardDetection) -> str:
    where = d.evidence.get("place", d.area_id)
    return f"{d.hazard.value} {d.severity} at {where}, {d.days_ahead} days ahead ({d.agreement:.0%} agree)"


def decide_flood_guide_mode(
    detections: list[HazardDetection], rules: dict, official_alert: str | None = None
) -> FloodGuideDecision:
    """detections: river-flood and heavy-rain detections for the area and its upstream points.

    official_alert: the highest official (CWC/IMD) flood or rain alert colour now, if any.
    """
    if official_alert == "red":
        return FloodGuideDecision(URGENT, ["official red alert"])

    rain = [d for d in detections if d.hazard is Hazard.HEAVY_RAIN]
    river = [d for d in detections if d.hazard is Hazard.RIVER_FLOOD]

    urgent = [
        d for d in rain
        if d.severity == rules["urgent_rain_category"] and d.days_ahead <= rules["urgent_within_days"]
    ]
    if urgent:
        return FloodGuideDecision(URGENT, [_describe(d) for d in urgent])

    prepare = [
        d for d in rain
        if d.severity in rules["prepare_rain_categories"] and d.days_ahead <= rules["prepare_within_days"]
    ] + [d for d in river if d.days_ahead <= rules["prepare_within_days"]]
    reasons = [_describe(d) for d in prepare]
    if official_alert == "orange":
        reasons.insert(0, "official orange alert")
    if reasons:
        return FloodGuideDecision(PREPARE, reasons)
    return FloodGuideDecision(None)


def keep_guide_on(
    today: FloodGuideDecision, today_date: date, last_signal: date | None, rules: dict
) -> FloodGuideDecision:
    """Once PREPARE has started, keep it on until stay_on_quiet_days mornings in a row show no
    flood signal. last_signal: the last morning that had one (from the guide's own history).
    A fresh signal always wins; URGENT is never held, it needs a live signal."""
    if today.mode or last_signal is None:
        return today
    quiet_days = (today_date - last_signal).days
    if 0 < quiet_days < rules["stay_on_quiet_days"]:
        return FloodGuideDecision(PREPARE, [f"staying on: flood signal on {last_signal.isoformat()}"])
    return today
