"""Scores a backtest against what actually happened, the way weather services verify forecasts.

For each hazard, every day in the window is one of:
- hit: it happened, and we had warned at least 1 day before;
- miss: it happened, and we had not warned;
- false alarm: we had warned for that day, and it did not happen;
(River floods are scored per flood-guide episode instead: see _flood_guide_score.)
- correct negative: no warning, nothing happened.

Probability of detection (POD) = hits / (hits + misses).
False-alarm ratio (FAR) = false alarms / (hits + false alarms).
Brier score (heat, 1 day ahead) = mean of (forecast probability - outcome)^2; 0 is perfect.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from weatherwise.backtest.backtest import (
    EXCESS_HEAT_DAY,
    HEAT_WAVE_DAY,
    HUMID_HEAT_DAY,
    RIVER_ABOVE_DAY,
    VERY_HEAVY_RAIN_DAY,
    Backtest,
)

MAX_LEAD_DAYS = 7


@dataclass
class HazardScore:
    hazard: str
    hits: int = 0
    misses: int = 0
    false_alarms: int = 0
    correct_negatives: int = 0
    event_lead_days: list[tuple[str, int | None]] = field(default_factory=list)  # (event start, lead)

    @property
    def pod(self) -> float | None:
        total = self.hits + self.misses
        return round(self.hits / total, 2) if total else None

    @property
    def far(self) -> float | None:
        total = self.hits + self.false_alarms
        return round(self.false_alarms / total, 2) if total else None

    def as_dict(self) -> dict:
        return {**asdict(self), "pod": self.pod, "far": self.far}


def _warned_days(bt: Backtest, matches) -> dict[date, int]:
    """Target day -> longest lead (days) at which a matching warning covered it."""
    warned: dict[date, int] = {}
    for bd in bt.days:
        for w in bd.warnings:
            if not matches(w):
                continue
            day = date.fromisoformat(w["first_day"])
            last = date.fromisoformat(w["last_day"])
            while day <= last:
                lead = (day - bd.day).days
                if 1 <= lead <= MAX_LEAD_DAYS:
                    warned[day] = max(warned.get(day, 0), lead)
                day += timedelta(days=1)
    return warned


def _guide_episodes(bt: Backtest) -> list[tuple[date, date]]:
    """Runs of consecutive days with the flood guide on: (first day, last day)."""
    episodes: list[tuple[date, date]] = []
    for bd in bt.days:
        if not bd.flood_guide_mode:
            continue
        if episodes and (bd.day - episodes[-1][1]).days == 1:
            episodes[-1] = (episodes[-1][0], bd.day)
        else:
            episodes.append((bd.day, bd.day))
    return episodes


def _flood_guide_score(bt: Backtest) -> HazardScore:
    """Scored per flood-guide episode (event-based), the standard for flood warnings: the
    guide starting is the warning; the days it stays on are the household's preparation, not
    new warnings. An episode is a hit if the river passes its flood level after it starts
    and within 7 days of it last being on."""
    score = HazardScore("river_flood")
    flood_days = [bd.day for bd in bt.days if RIVER_ABOVE_DAY in bd.observed_events]
    episodes = _guide_episodes(bt)
    for start, end in episodes:
        if any(start < f <= end + timedelta(days=MAX_LEAD_DAYS) for f in flood_days):
            score.hits += 1
        else:
            score.false_alarms += 1
    previous = None
    for f in flood_days:
        if previous is None or (f - previous).days > 1:  # first day of each flood
            leads = [(f - start).days for start, end in episodes
                     if start < f <= end + timedelta(days=MAX_LEAD_DAYS)]
            score.event_lead_days.append((f.isoformat(), max(leads) if leads else None))
            if not leads:
                score.misses += 1
        previous = f
    return score


def _score(bt: Backtest, hazard: str, event: str, warned: dict[date, int]) -> HazardScore:
    score = HazardScore(hazard)
    in_event = False
    for bd in bt.days:
        happened = event in bd.observed_events
        was_warned = bd.day in warned
        if happened and was_warned:
            score.hits += 1
        elif happened:
            score.misses += 1
        elif was_warned:
            score.false_alarms += 1
        else:
            score.correct_negatives += 1
        if happened and not in_event:
            score.event_lead_days.append((bd.day.isoformat(), warned.get(bd.day)))
        in_event = happened
    return score


def verify(bt: Backtest) -> dict:
    if bt.mode != "as_issued":
        return {
            "mode": bt.mode,
            "note": bt.notes[0],
            "conditions_met": {
                bd.day.isoformat(): bd.observed_events for bd in bt.days if bd.observed_events
            },
        }

    local = bt.place["name"]
    scores = [
        _score(bt, "heat_wave", HEAT_WAVE_DAY,
               _warned_days(bt, lambda w: w["hazard"] == "heat_wave")),
        _score(bt, "humid_heat", HUMID_HEAT_DAY,
               _warned_days(bt, lambda w: w["hazard"] == "humid_heat")),
        _score(bt, "excess_heat", EXCESS_HEAT_DAY,
               _warned_days(bt, lambda w: w["hazard"] == "excess_heat")),
        _score(bt, "very_heavy_rain", VERY_HEAVY_RAIN_DAY,
               _warned_days(bt, lambda w: w["hazard"] == "heavy_rain" and w["place"] == local
                            and w["severity"] in ("very_heavy", "extremely_heavy"))),
    ]
    if bt.flood_level_m3s is not None:
        scores.append(_flood_guide_score(bt))

    outcomes = {
        bd.day: 1.0 if HEAT_WAVE_DAY in bd.observed_events else 0.0 for bd in bt.days
    }
    pairs = [(p, outcomes[d]) for d, p in bt.heat_probabilities if d in outcomes]
    brier = round(sum((p - o) ** 2 for p, o in pairs) / len(pairs), 3) if pairs else None

    return {
        "mode": bt.mode,
        "scores": {s.hazard: s.as_dict() for s in scores},
        "heat_brier_score_1_day_ahead": brier,
        "notes": bt.notes,
    }
