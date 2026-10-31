"""Backtest any place and dates: what we would have sent each morning, and what happened.

Rules that keep it honest:
- forecasts are the 7-model archive as issued about a day before each 6 AM scan;
- the flood level uses only river history from years BEFORE the backtest;
- "what happened" (ERA5 reanalysis, GloFAS reconstructed river flow) is used only to score;
- before the archive starts (2024), we can only check whether real conditions met our
  rules ("conditions only"), never claim a lead time.
Official alerts are not archived, so backtests show our own signals alone.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from weatherwise.places.resolve import PlaceContext
from weatherwise.risk.flood_guide_trigger import decide_flood_guide_mode, keep_guide_on
from weatherwise.risk.forecast_agreement import consecutive_day_spans
from weatherwise.risk.heat_wave import (
    HEAT_WAVE,
    detect_excess_heat,
    detect_heat_wave,
    detect_humid_heat,
    excess_heat_factor,
    heat_wave_severity,
)
from weatherwise.risk.heavy_rain import detect_heavy_rain
from weatherwise.risk.models import ForecastDataMissing, Hazard, HazardDetection
from weatherwise.weather import open_meteo as om
from weatherwise.weather.service import WeatherService

AS_ISSUED_ARCHIVE_START = date(2024, 1, 1)

# Observed event names, also used by verification.
HEAT_WAVE_DAY, HUMID_HEAT_DAY, EXCESS_HEAT_DAY, VERY_HEAVY_RAIN_DAY, RIVER_ABOVE_DAY = (
    "heat_wave", "humid_heat", "excess_heat", "very_heavy_rain", "river_above_flood_level")
OBSERVED_LOOKBACK_DAYS = 32  # Excess Heat Factor needs the 30 days before each day


@dataclass
class BacktestDay:
    day: date
    warnings: list[dict] = field(default_factory=list)  # detections issued this morning
    flood_guide_mode: str | None = None
    flood_guide_reasons: list[str] = field(default_factory=list)
    observed: dict = field(default_factory=dict)
    observed_events: list[str] = field(default_factory=list)
    data_missing: list[str] = field(default_factory=list)


@dataclass
class Backtest:
    place: dict
    first_day: date
    last_day: date
    mode: str  # "as_issued" or "conditions_only"
    flood_level_m3s: float | None
    days: list[BacktestDay]
    heat_probabilities: list[tuple[date, float]] = field(default_factory=list)  # 1-day-ahead
    notes: list[str] = field(default_factory=list)


def _span(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def gather_inputs(place: PlaceContext, first: date, last: date, weather: WeatherService,
                  rules: dict) -> dict:
    """All raw inputs for a backtest (savable as a snapshot so tests run offline)."""
    inputs: dict = {
        "normal_tmax": weather.normal_tmax(place.cell),
        "heat_climate": weather.heat_climate(place.cell, rules),
        "observed": weather.observed_daily(
            place, first - timedelta(days=OBSERVED_LOOKBACK_DAYS), last + timedelta(days=2)),
    }
    if first >= AS_ISSUED_ARCHIVE_START:
        target_last = last + timedelta(days=om.MAX_PREVIOUS_DAY)
        inputs["heat_as_issued"] = weather.heat_as_issued(place, first, target_last)
        rain_places = [(place.name, place)] + [(p.name, p) for p in place.river.upstream_rain_points]
        inputs["rain_as_issued"] = {
            name: weather.rain_as_issued(p, first, target_last) for name, p in rain_places
        }
    if place.river.is_river_area:
        r = place.river
        inputs["flood_level_m3s"] = weather.flood_level(r.river_lat, r.river_lon, rules, first.year - 1)
        inputs["river_observed"] = weather.river_archive(
            r.river_lat, r.river_lon, first, last, om.RIVER_REANALYSIS_MODEL)
        if first >= AS_ISSUED_ARCHIVE_START:
            inputs["river_archived_forecast"] = weather.river_archive(
                r.river_lat, r.river_lon, first, last, om.RIVER_FORECAST_ARCHIVE_MODEL)
    return inputs


def _observed_events(place: PlaceContext, days: list[date], inputs: dict, rules: dict) -> dict:
    """What actually happened each day, judged by the same rules we warn with."""
    obs = {
        v: om.parse_daily_values(inputs["observed"], v)
        for v in ("temperature_2m_max", "temperature_2m_mean", "apparent_temperature_max",
                  "precipitation_sum")
    }
    climate = inputs["heat_climate"]

    def observed_ehf(d: date) -> float | None:
        window = [obs["temperature_2m_mean"].get(d + timedelta(days=k)) for k in range(3)]
        previous = [obs["temperature_2m_mean"].get(d - timedelta(days=k)) for k in range(30, 0, -1)]
        if any(v is None for v in window + previous):
            return None
        return excess_heat_factor(window, previous, climate["t95"])
    river = om.parse_daily_values(inputs["river_observed"], "river_discharge") \
        if "river_observed" in inputs else {}
    level = inputs.get("flood_level_m3s")
    normals = inputs["normal_tmax"]
    heat, humid = rules["heat"], rules["humid_heat"]

    heat_flags = [
        d in obs["temperature_2m_max"] and heat_wave_severity(
            obs["temperature_2m_max"][d], normals[d.strftime("%m-%d")], place.terrain, heat) >= HEAT_WAVE
        for d in days
    ]
    heat_days = {
        days[i]
        for start, end in consecutive_day_spans(heat_flags)
        if end - start + 1 >= heat["min_consecutive_days"]
        for i in range(start, end + 1)
    }

    events = {}
    for d in days:
        e = []
        if d in heat_days:
            e.append(HEAT_WAVE_DAY)
        if obs["apparent_temperature_max"].get(d, -99) >= humid["apparent_tmax_danger"]:
            e.append(HUMID_HEAT_DAY)
        ehf = observed_ehf(d)
        if ehf is not None and ehf > 0:
            e.append(EXCESS_HEAT_DAY)
        if obs["precipitation_sum"].get(d, 0) >= rules["heavy_rain"]["very_heavy"]:
            e.append(VERY_HEAVY_RAIN_DAY)
        if level is not None and river.get(d, 0) >= level:
            e.append(RIVER_ABOVE_DAY)
        events[d] = (e, {
            "tmax": obs["temperature_2m_max"].get(d),
            "normal_tmax": normals[d.strftime("%m-%d")],
            "feels_like_max": obs["apparent_temperature_max"].get(d),
            "excess_heat_factor": None if ehf is None else round(ehf, 2),
            "rain_mm": obs["precipitation_sum"].get(d),
            "river_m3s": river.get(d),
        })
    return events


def _as_dict(d: HazardDetection) -> dict:
    return {
        "hazard": d.hazard.value, "severity": d.severity, "first_day": d.first_day.isoformat(),
        "last_day": d.last_day.isoformat(), "days_ahead": d.days_ahead,
        "agreement": d.agreement, "place": d.evidence.get("place"),
    }


def run_backtest(place: PlaceContext, first: date, last: date, inputs: dict,
                 rules: dict) -> Backtest:
    days = _span(first, last)
    mode = "as_issued" if first >= AS_ISSUED_ARCHIVE_START else "conditions_only"
    area = place.as_area()
    normals = inputs["normal_tmax"]
    level = inputs.get("flood_level_m3s")
    archived_flow = om.parse_daily_values(inputs["river_archived_forecast"], "river_discharge") \
        if "river_archived_forecast" in inputs else {}
    events = _observed_events(place, days, inputs, rules)

    result = Backtest(place.summary(), first, last, mode, level, [])
    if mode == "conditions_only":
        result.notes.append(
            "No archived forecasts before 2024: shows whether real conditions met our rules, "
            "not how early we would have warned.")
    result.notes.append("Official alerts are not archived; only our own signals are shown.")

    last_flood_signal: date | None = None
    for d in days:
        bd = BacktestDay(d, observed=events[d][1], observed_events=events[d][0])
        if mode == "as_issued":
            detections: list[HazardDetection] = []
            try:
                tmax = om.parse_as_issued(inputs["heat_as_issued"], d, "temperature_2m", "max")
                normal_by_date = {x: normals[x.strftime("%m-%d")] for x in tmax.dates}
                detections += detect_heat_wave(area, tmax, normal_by_date, d, rules["heat"])
                if len(tmax.dates) > 1:
                    next_day = [v for v in tmax.values[1] if v is not None]
                    share = sum(
                        heat_wave_severity(v, normal_by_date[tmax.dates[1]], place.terrain,
                                           rules["heat"]) >= HEAT_WAVE for v in next_day
                    ) / len(next_day)
                    result.heat_probabilities.append((tmax.dates[1], share))
                feels = om.parse_as_issued(inputs["heat_as_issued"], d, "apparent_temperature", "max")
                detections += detect_humid_heat(area, feels, d, rules["humid_heat"])
                means = om.parse_as_issued(inputs["heat_as_issued"], d, "temperature_2m", "mean")
                previous = om.parse_past_daily_means(inputs["observed"], d)
                detections += detect_excess_heat(
                    area, means, previous, inputs["heat_climate"], d, rules["excess_heat"])
            except ForecastDataMissing:
                bd.data_missing.append("heat forecast")
            for name, raw in inputs.get("rain_as_issued", {}).items():
                try:
                    rain = om.parse_rain_as_issued(raw, d)
                    detections += detect_heavy_rain(area, rain, d, rules["heavy_rain"], place=name)
                except ForecastDataMissing:
                    bd.data_missing.append(f"rain forecast at {name}")
            flow = archived_flow.get(d)
            if level is not None and flow is not None and flow >= level:
                detections.append(HazardDetection(
                    area.id, Hazard.RIVER_FLOOD, "above_flood_level", d, d, 0, 1.0,
                    {"place": place.name, "archived_forecast_m3s": flow}))
            decision = decide_flood_guide_mode(detections, rules["flood_guide"])
            if decision.mode:
                last_flood_signal = d
            decision = keep_guide_on(decision, d, last_flood_signal, rules["flood_guide"])
            bd.warnings = [_as_dict(x) for x in detections]
            bd.flood_guide_mode, bd.flood_guide_reasons = decision.mode, decision.reasons
        result.days.append(bd)
    return result


def backtest_place(place: PlaceContext, first: date, last: date, weather: WeatherService,
                   rules: dict) -> Backtest:
    return run_backtest(place, first, last, gather_inputs(place, first, last, weather, rules), rules)
