"""Shared helpers: how many forecast runs agree, and spans of consecutive days."""

from collections.abc import Callable
from datetime import date

from weatherwise.risk.models import EnsembleForecast, ForecastDataMissing

MIN_FORECAST_RUNS = 5


def share_of_runs_agreeing(
    forecast: EnsembleForecast, condition: Callable[[int, float], bool]
) -> list[float]:
    """Per day, the share of forecast runs where condition(day_index, value) holds.

    Raises ForecastDataMissing if any day has fewer than MIN_FORECAST_RUNS values.
    """
    shares = []
    for i, run_values in enumerate(forecast.values):
        valid = [v for v in run_values if v is not None]
        if len(valid) < MIN_FORECAST_RUNS:
            raise ForecastDataMissing(f"{forecast.dates[i]}: only {len(valid)} forecast runs")
        shares.append(sum(1 for v in valid if condition(i, v)) / len(valid))
    return shares


def consecutive_day_spans(flags: list[bool]) -> list[tuple[int, int]]:
    """Inclusive (start, end) day indexes of consecutive True values."""
    spans, start = [], None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            spans.append((start, i - 1))
            start = None
    if start is not None:
        spans.append((start, len(flags) - 1))
    return spans


def days_ahead(day: date, issue_date: date) -> int:
    return (day - issue_date).days
