"""Forecast correction (ours): each forecast model runs a little warm or cool at each place.

Every morning we compare each model's day-ahead forecasts for the last few weeks at this place
with what happened (ERA5 reanalysis, the same record the replays are scored against), and shift
today's forecast by the average difference. Rules in [forecast_correction]:

- temperatures only (max, feels-like max, mean): rain errors are not a simple shift, so rain
  is judged against the place's own history instead (heavy_rain.detect_unusual_rain);
- shifts go both ways (allow_cooling = false shifts only warmer; measured worse on the Akola
  replay: models that run hot stayed hot, and false alarms rose);
- each shift is capped at max_shift_c, and too little history means no shift at all.

What this does not fix: ERA5 is itself a ~25 km average, cooler than a station thermometer
on the hottest days (Akola, April 2026: station 46.9 C, grid ~43.6 C). Our work-heat levels
are set with that gap in mind.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean

from weatherwise.risk.models import EnsembleForecast
from weatherwise.weather import open_meteo as om

# What we correct: name -> (hourly variable in the forecast archive, how a day is made from
# its hours, the daily variable in "what happened").
CORRECTED = {
    "tmax": ("temperature_2m", "max", "temperature_2m_max"),
    "feels_like_tmax": ("apparent_temperature", "max", "apparent_temperature_max"),
    "mean_temp": ("temperature_2m", "mean", "temperature_2m_mean"),
}

DayAhead = dict[date, tuple[float | None, ...]]  # day -> each model's forecast, issued the day before


@dataclass(frozen=True)
class Correction:
    """Learned shifts, deg C: name -> one per forecast run, or one for every run."""

    shifts: dict[str, tuple[float, ...]] = field(default_factory=dict)
    status: str = "off"  # "on"; "off" (switched off in the rules); "unavailable" (archive not
    #                      reached); "no_history" (reached, but too few days to learn from)

    def apply(self, name: str, forecast: EnsembleForecast | None) -> EnsembleForecast | None:
        shifts = self.shifts.get(name)
        if forecast is None or not shifts or not any(shifts):
            return forecast
        n_runs = len(forecast.values[0]) if forecast.values else 0
        if len(shifts) not in (1, n_runs):
            raise ValueError(f"{name}: {len(shifts)} shifts for {n_runs} forecast runs")

        def shift(r: int) -> float:
            return shifts[0] if len(shifts) == 1 else shifts[r]

        return EnsembleForecast(forecast.dates, tuple(
            tuple(None if v is None else round(v + shift(r), 2) for r, v in enumerate(row))
            for row in forecast.values))

    def summary(self) -> dict:
        """For the outlook: the status and, per variable, the average shift."""
        return {"status": self.status,
                "shift_c": {k: round(mean(v), 1) for k, v in self.shifts.items() if v}}


OFF = Correction()
UNAVAILABLE = Correction(status="unavailable")


def training_window(issue_date: date, rules: dict) -> tuple[date, date]:
    """The days whose errors are learned from: what happened is known ~5 days late."""
    last = issue_date - timedelta(days=rules["observed_delay_days"])
    return last - timedelta(days=rules["training_days"] - 1), last


def learn_shift(errors: list[float], rules: dict) -> float:
    """The average of (what happened - forecast), within the rules' limits."""
    if len(errors) < rules["min_training_days"]:
        return 0.0
    shift = mean(errors)
    if not rules["allow_cooling"]:
        shift = max(shift, 0.0)
    cap = rules["max_shift_c"]
    return round(max(-cap, min(cap, shift)), 2)


def _errors(day_ahead: DayAhead, observed: dict[date, float], first: date, last: date) -> list[list[float]]:
    """Per forecast run (model): what happened - its day-ahead forecast, each day first to last."""
    n_runs = max((len(row) for row in day_ahead.values()), default=0)
    errors: list[list[float]] = [[] for _ in range(n_runs)]
    day = first
    while day <= last:
        row, happened = day_ahead.get(day), observed.get(day)
        if row is not None and happened is not None:
            for r, v in enumerate(row):
                if v is not None:
                    errors[r].append(happened - v)
        day += timedelta(days=1)
    return errors


def learn_shifts(day_ahead: DayAhead, observed: dict[date, float], first: date, last: date,
                 rules: dict) -> tuple[float, ...]:
    """One shift per forecast run (model), from its day-ahead forecasts from first to last."""
    return tuple(learn_shift(e, rules) for e in _errors(day_ahead, observed, first, last))


def learn_from_series(day_ahead: dict[str, DayAhead], observed: dict[str, dict[date, float]],
                      issue_date: date, rules: dict) -> Correction:
    """The correction for one morning, from already-parsed archives (replays parse them once)."""
    if not rules["enabled"]:
        return OFF
    first, last = training_window(issue_date, rules)
    errors = {name: _errors(day_ahead[name], observed[name], first, last) for name in CORRECTED}
    learned = any(len(e) >= rules["min_training_days"] for runs in errors.values() for e in runs)
    if not learned:  # said plainly: an archive that answered with nothing must not look like "on"
        return Correction(status="no_history")
    return Correction({name: tuple(learn_shift(e, rules) for e in runs) for name, runs in errors.items()},
                      status="on")


def parse_series(issued_raw: dict, observed_raw: dict,
                 models: tuple[str, ...]) -> tuple[dict[str, DayAhead], dict[str, dict[date, float]]]:
    day_ahead = {name: om.parse_day_ahead(issued_raw, var, how, models)
                 for name, (var, how, _) in CORRECTED.items()}
    observed = {name: om.parse_daily_values(observed_raw, obs) for name, (_, _, obs) in CORRECTED.items()}
    return day_ahead, observed


def learn(inputs: dict | None, issue_date: date, rules: dict, models: tuple[str, ...]) -> Correction:
    """The correction for one morning from raw archives {"issued": ..., "observed": ...}.
    No inputs (the archive could not be reached) means no shift, reported as "unavailable"."""
    if not rules["enabled"]:
        return OFF
    if not inputs:
        return UNAVAILABLE
    day_ahead, observed = parse_series(inputs["issued"], inputs["observed"], models)
    return learn_from_series(day_ahead, observed, issue_date, rules)
