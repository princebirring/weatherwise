"""Decides whether the flood guide starts in prepare or urgent mode (plan §4.3, §5.2, §6.1).

Safety rule: our own model data (river forecast, heavy rain) only ever starts PREPARE.
URGENT ("move now") needs an official red alert, or extremely heavy rain in the area or
upstream within urgent_within_days. We never tell a family to move on our model alone.

What starts PREPARE is a list of named signals in [flood_guide] prepare_signals (PREPARE_SIGNALS
below), so each one can be switched off in the rules without touching code.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

from weatherwise.risk.models import Hazard, HazardDetection

PREPARE, URGENT = "prepare", "urgent"


@dataclass(frozen=True)
class FloodGuideDecision:
    mode: str | None  # None, PREPARE, or URGENT
    reasons: list[str] = field(default_factory=list)


def _describe(d: HazardDetection) -> str:
    where = d.evidence.get("place", d.area_id)
    return f"{d.hazard.value} {d.severity} at {where}, {d.days_ahead} days ahead ({d.agreement:.0%} agree)"


def _soon(detections: list[HazardDetection], rules: dict) -> list[HazardDetection]:
    return [d for d in detections if d.days_ahead <= rules["prepare_within_days"]]


def _very_heavy_rain(detections: list[HazardDetection], rules: dict) -> list[HazardDetection]:
    """IMD very heavy or extremely heavy rain, in the area or upstream."""
    return [d for d in _soon(detections, rules) if d.hazard is Hazard.HEAVY_RAIN
            and d.severity in ("very_heavy", "extremely_heavy")]


def _heavy_rain_days_in_a_row(detections: list[HazardDetection], rules: dict) -> list[HazardDetection]:
    """Heavy rain (any IMD category) on heavy_rain_days_in_a_row days running at one place:
    soaked ground and full streams flood even when no single day is extreme."""
    need = rules["heavy_rain_days_in_a_row"]
    rain = [d for d in detections if d.hazard is Hazard.HEAVY_RAIN]
    days_at = {(d.evidence.get("place"), d.first_day) for d in rain}
    return [
        d for d in _soon(rain, rules)
        if all((d.evidence.get("place"), d.first_day + timedelta(days=k)) in days_at for k in range(need))
    ][:1]  # one reason is enough: the run of days is described by its first day


def _unusual_rain(detections: list[HazardDetection], rules: dict) -> list[HazardDetection]:
    """Rain rare for this place (ours)."""
    return [d for d in _soon(detections, rules) if d.hazard is Hazard.UNUSUAL_RAIN]


def _river_flood(detections: list[HazardDetection], rules: dict) -> list[HazardDetection]:
    """The large river forecast to pass its flood level."""
    return [d for d in _soon(detections, rules) if d.hazard is Hazard.RIVER_FLOOD]


PREPARE_SIGNALS: dict[str, Callable[[list[HazardDetection], dict], list[HazardDetection]]] = {
    "very_heavy_rain": _very_heavy_rain,
    "heavy_rain_days_in_a_row": _heavy_rain_days_in_a_row,
    "unusual_rain": _unusual_rain,
    "river_flood": _river_flood,
}


def decide_flood_guide_mode(
    detections: list[HazardDetection], rules: dict, official_alert: str | None = None
) -> FloodGuideDecision:
    """detections: the scan's detections (rain and river ones for the area and its upstream points
    are used; the rest are ignored).

    official_alert: the highest official (CWC/IMD) flood or rain alert colour now, if any.
    """
    if official_alert == "red":
        return FloodGuideDecision(URGENT, ["official red alert"])

    urgent = [
        d for d in detections
        if d.hazard is Hazard.HEAVY_RAIN and d.severity == rules["urgent_rain_category"]
        and d.days_ahead <= rules["urgent_within_days"]
    ]
    if urgent:
        return FloodGuideDecision(URGENT, [_describe(d) for d in urgent])

    reasons = [f"{name}: {_describe(d)}" for name in rules["prepare_signals"]
               for d in PREPARE_SIGNALS[name](detections, rules)]
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
