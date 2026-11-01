"""Flow 1 triggers: official heat-wave rules, and our own heat rules: feels-like heat for
outdoor work, and the Excess Heat Factor (plan §5.2).

Each country names its official rule in [heat] rule = "..."; HEAT_WAVE_RULES maps
that name to a function. A country with a different definition adds a function
here and changes nothing else.
"""

from collections.abc import Callable
from datetime import date

from weatherwise.risk.forecast_agreement import (
    MIN_FORECAST_RUNS,
    consecutive_day_spans,
    days_ahead,
    share_of_runs_agreeing,
)
from weatherwise.risk.models import (
    Area,
    EnsembleForecast,
    ForecastDataMissing,
    Hazard,
    HazardDetection,
    TerrainZone,
)

NONE, HEAT_WAVE, SEVERE = 0, 1, 2


def imd_heat_wave_severity(tmax: float, normal: float, terrain: TerrainZone, rules: dict) -> int:
    """IMD definition, for one day of one forecast run: NONE, HEAT_WAVE, or SEVERE."""
    if tmax < rules["base_tmax"][terrain.value]:
        return NONE
    departure = tmax - normal
    if terrain is TerrainZone.PLAINS and tmax >= rules["severe_absolute"]:
        return SEVERE
    if departure > rules["severe_departure_above"]:
        return SEVERE
    if terrain is TerrainZone.PLAINS and tmax >= rules["heat_wave_absolute"]:
        return HEAT_WAVE
    if departure >= rules["heat_wave_departure"]:
        return HEAT_WAVE
    return NONE


HEAT_WAVE_RULES: dict[str, Callable[[float, float, TerrainZone, dict], int]] = {
    "imd": imd_heat_wave_severity,
}


def heat_wave_severity(tmax: float, normal: float, terrain: TerrainZone, rules: dict) -> int:
    """Apply the region's official heat-wave rule."""
    name = rules.get("rule")
    if name not in HEAT_WAVE_RULES:
        raise ValueError(f"unknown heat-wave rule {name!r}; known: {sorted(HEAT_WAVE_RULES)}")
    return HEAT_WAVE_RULES[name](tmax, normal, terrain, rules)


def detect_heat_wave(
    area: Area,
    tmax: EnsembleForecast,
    normal_tmax: dict[date, float],
    issue_date: date,
    rules: dict,
) -> list[HazardDetection]:
    """Heat-wave spans that enough forecast runs agree on, within the warning horizon."""

    def severity(i: int, v: float) -> int:
        return heat_wave_severity(v, normal_tmax[tmax.dates[i]], area.terrain, rules)

    heat_share = share_of_runs_agreeing(tmax, lambda i, v: severity(i, v) >= HEAT_WAVE)
    severe_share = share_of_runs_agreeing(tmax, lambda i, v: severity(i, v) >= SEVERE)
    agreed = [s >= rules["min_agreement"] for s in heat_share]
    max_days_ahead = rules["first_warning_lead_days"][1]

    detections = []
    for start, end in consecutive_day_spans(agreed):
        if end - start + 1 < rules["min_consecutive_days"]:
            continue
        ahead = days_ahead(tmax.dates[start], issue_date)
        if ahead > max_days_ahead:
            continue
        severe = any(severe_share[i] >= rules["min_agreement"] for i in range(start, end + 1))
        detections.append(
            HazardDetection(
                area_id=area.id,
                hazard=Hazard.HEAT_WAVE,
                severity="severe" if severe else "heat_wave",
                first_day=tmax.dates[start],
                last_day=tmax.dates[end],
                days_ahead=ahead,
                agreement=round(min(heat_share[start : end + 1]), 2),
                evidence={
                    "terrain": area.terrain.value,
                    "hottest_run_tmax": max(
                        v for day in tmax.values[start : end + 1] for v in day if v is not None
                    ),
                    "normal_tmax": [normal_tmax[d] for d in tmax.dates[start : end + 1]],
                },
            )
        )
    return detections


def detect_work_heat(
    area: Area, feels_like_tmax: EnsembleForecast, issue_date: date, rules: dict
) -> list[HazardDetection]:
    """Our health line for outdoor work: feels-like heat (temperature and humidity) at or above
    each level in rules["levels"] (lowest first). Labelled as ours: it is not IMD's heat-wave label.

    One detection per span of days at the lowest level or above; its severity is the highest
    level enough runs agree on for any day in the span.
    """
    levels = sorted(rules["levels"], key=lambda lv: lv["feels_like_c"])
    shares = [share_of_runs_agreeing(feels_like_tmax, lambda i, v, c=lv["feels_like_c"]: v >= c)
              for lv in levels]
    agreed = [s >= rules["min_agreement"] for s in shares[0]]

    detections = []
    for start, end in consecutive_day_spans(agreed):
        if end - start + 1 < rules["min_consecutive_days"]:
            continue
        top = max(k for k, share in enumerate(shares)
                  if any(share[i] >= rules["min_agreement"] for i in range(start, end + 1)))
        detections.append(
            HazardDetection(
                area_id=area.id,
                hazard=Hazard.WORK_HEAT,
                severity=levels[top]["name"],
                first_day=feels_like_tmax.dates[start],
                last_day=feels_like_tmax.dates[end],
                days_ahead=days_ahead(feels_like_tmax.dates[start], issue_date),
                agreement=round(min(shares[0][start : end + 1]), 2),
                evidence={"rule": "ours (feels-like heat for outdoor work)",
                          "feels_like_c": levels[top]["feels_like_c"]},
            )
        )
    return detections


def work_heat_level(feels_like_c: float, rules: dict) -> str | None:
    """The highest work-heat level a feels-like temperature reaches (for scoring), or None."""
    reached = [lv for lv in rules["levels"] if feels_like_c >= lv["feels_like_c"]]
    return max(reached, key=lambda lv: lv["feels_like_c"])["name"] if reached else None


# ---- Excess Heat Factor (ours) ---------------------------------------------------------


def excess_heat_factor(next_3_day_means: list[float], previous_30_day_means: list[float],
                       t95: float) -> float:
    """EHF = EHI_sig * max(1, EHI_accl) (Nairn & Fawcett 2015). > 0 means a heatwave.

    EHI_sig: how far the 3-day mean is above this place's 95th-percentile daily mean.
    EHI_accl: how far it is above the previous 30 days (people have not acclimatised).
    """
    three_day = sum(next_3_day_means) / 3
    significance = three_day - t95
    acclimatisation = three_day - sum(previous_30_day_means) / 30
    return significance * max(1.0, acclimatisation)


def heat_climate(daily_means: list[float], heat_percentile: float,
                 severe_percentile: float) -> dict:
    """A place's EHF baseline from decades of daily mean temperature (no gaps expected)."""
    ordered = sorted(daily_means)
    t95 = ordered[min(len(ordered) - 1, int(heat_percentile / 100 * len(ordered)))]
    positive = sorted(
        e for i in range(30, len(daily_means) - 2)
        if (e := excess_heat_factor(daily_means[i:i + 3], daily_means[i - 30:i], t95)) > 0
    )
    ehf_severe = positive[min(len(positive) - 1, int(severe_percentile / 100 * len(positive)))] \
        if positive else float("inf")
    return {"t95": round(t95, 2), "ehf_severe": round(ehf_severe, 2)}


def detect_excess_heat(
    area: Area,
    mean_temp: EnsembleForecast,
    previous_30_day_means: list[float],
    climate: dict,
    issue_date: date,
    rules: dict,
) -> list[HazardDetection]:
    """Days enough forecast runs put above this place's own heatwave line (EHF > 0).

    previous_30_day_means: observed daily means for the 30 days before the first forecast day.
    """
    if len(previous_30_day_means) < 30:
        raise ForecastDataMissing("need 30 days of observed mean temperature before the forecast")
    n_days = len(mean_temp.dates) - 2  # each EHF needs this day and the next two
    if n_days < 1:
        return []
    n_runs = len(mean_temp.values[0])
    heat_share, severe_share = [], []
    for i in range(n_days):
        heat = severe = valid = 0
        for r in range(n_runs):
            run = [mean_temp.values[d][r] for d in range(i + 3)]
            if any(v is None for v in run):
                continue
            history = (previous_30_day_means + run[:i])[-30:]
            ehf = excess_heat_factor(run[i:i + 3], history, climate["t95"])
            valid += 1
            heat += ehf > 0
            severe += ehf >= climate["ehf_severe"]
        if valid < MIN_FORECAST_RUNS:
            raise ForecastDataMissing(f"{mean_temp.dates[i]}: only {valid} forecast runs")
        heat_share.append(heat / valid)
        severe_share.append(severe / valid)

    agreed = [s >= rules["min_agreement"] for s in heat_share]
    detections = []
    for start, end in consecutive_day_spans(agreed):
        if end - start + 1 < rules["min_consecutive_days"]:
            continue
        severe = any(severe_share[i] >= rules["min_agreement"] for i in range(start, end + 1))
        detections.append(
            HazardDetection(
                area_id=area.id,
                hazard=Hazard.EXCESS_HEAT,
                severity="severe" if severe else "heatwave",
                first_day=mean_temp.dates[start],
                last_day=mean_temp.dates[end],
                days_ahead=days_ahead(mean_temp.dates[start], issue_date),
                agreement=round(min(heat_share[start:end + 1]), 2),
                evidence={"rule": "ours (Excess Heat Factor)", "t95": climate["t95"]},
            )
        )
    return detections
