"""Open-Meteo parsing: ensembles, archives as issued, baselines, recent conditions."""

from datetime import date

import pytest

from weatherwise.risk.models import ForecastDataMissing
from weatherwise.weather import open_meteo as om


def _daily(var: str, days: list[str], runs: list[list[float | None]]) -> dict:
    """Fake ensemble response: runs[r][d] for the control run and members."""
    daily = {"time": days, var: runs[0]}
    for r, values in enumerate(runs[1:], start=1):
        daily[f"{var}_member{r:02d}"] = values
    return {"daily": daily}


class TestParseEnsemble:
    def test_empty_days_past_the_model_range_are_dropped(self):
        raw = _daily("temperature_2m_max", ["2026-04-10", "2026-04-11"], [[40.0, None]] * 6)
        assert om.parse_ensemble(raw, "temperature_2m_max").dates == (date(2026, 4, 10),)

    def test_gaps_inside_the_range_are_kept_as_missing(self):
        raw = _daily("temperature_2m_max", ["2026-04-10", "2026-04-11"], [[None, 40.0]] * 6)
        f = om.parse_ensemble(raw, "temperature_2m_max")
        assert len(f.dates) == 2 and f.values[0] == (None,) * 6

    def test_negative_rain_is_set_to_zero(self):
        raw = _daily("precipitation_sum", ["2026-04-10"], [[-0.1]] * 6)
        assert om.parse_ensemble(raw, "precipitation_sum").values[0] == (0.0,) * 6

    def test_control_run_plus_members(self):
        raw = _daily("precipitation_sum", ["2026-04-10"], [[1.0]] * 51)
        assert len(om.parse_ensemble(raw, "precipitation_sum").values[0]) == 51


def _as_issued(variable: str, first: date, n_days: int, value_for) -> dict:
    """Fake Previous Runs response: value_for(model, previous_day, day_index) per hour."""
    times = [f"{date.fromordinal(first.toordinal() + d).isoformat()}T{h:02d}:00"
             for d in range(n_days) for h in range(24)]
    hourly = {"time": times}
    for model in om.AS_ISSUED_MODELS:
        for k in range(1, om.MAX_PREVIOUS_DAY + 1):
            hourly[f"{variable}_previous_day{k}_{model}"] = [
                value_for(model, k, i // 24) for i in range(len(times))]
    return {"hourly": hourly}


class TestParseAsIssued:
    def test_day_k_uses_forecasts_issued_k_plus_1_days_before(self):
        raw = _as_issued("precipitation", date(2024, 7, 20), 8, lambda m, k, d: float(k))
        f = om.parse_rain_as_issued(raw, date(2024, 7, 20))
        assert f.values[0][0] == 24.0       # today: previous_day1, 1 mm x 24 h
        assert f.values[3][0] == 4 * 24.0   # 3 days ahead: previous_day4
        assert len(f.values[0]) == len(om.AS_ISSUED_MODELS)

    def test_daily_max_and_mean_for_temperature(self):
        raw = _as_issued("temperature_2m", date(2026, 4, 20), 8,
                         lambda m, k, d: 30.0 if d == 0 else 40.0)
        assert om.parse_as_issued(raw, date(2026, 4, 20), "temperature_2m", "max").values[1][0] == 40.0
        assert om.parse_as_issued(raw, date(2026, 4, 20), "temperature_2m", "mean").values[0][0] == 30.0

    def test_too_few_models_is_missing_data(self):
        raw = _as_issued("precipitation", date(2024, 7, 20), 8, lambda m, k, d: None)
        with pytest.raises(ForecastDataMissing):
            om.parse_rain_as_issued(raw, date(2024, 7, 20))


class TestBaselines:
    def _history(self, peaks: list[float]) -> dict:
        days, flows = [], []
        for year, peak in zip(range(1990, 1990 + len(peaks)), peaks, strict=True):
            days += [f"{year}-07-01", f"{year}-08-01"]
            flows += [10.0, peak]
        return {"daily": {"time": days, "river_discharge": flows}}

    def test_flood_level_by_return_period(self):
        raw = self._history([100.0 * i for i in range(1, 20)])  # 19 years: 100..1900
        assert om.parse_flood_level(raw, 2) == 1000.0   # rank 10 of 19: the median
        assert om.parse_flood_level(raw, 5) == 1600.0   # rank 16 of 19
        assert om.parse_flood_level(raw, 100) == 1900.0  # beyond the record: the highest

    def test_flood_level_needs_ten_years(self):
        with pytest.raises(ValueError):
            om.parse_flood_level(self._history([500.0] * 9), 5)

    def test_normal_tmax_is_smoothed_mean(self):
        start = date(2001, 1, 1).toordinal()
        days = [date.fromordinal(start + i) for i in range(365)]
        temps = [47.0 if d == date(2001, 5, 15) else 40.0 for d in days]
        raw = {"daily": {"time": [d.isoformat() for d in days], "temperature_2m_max": temps}}
        assert om.parse_normal_tmax(raw, window_days=0)["05-15"] == 47.0
        assert om.parse_normal_tmax(raw, window_days=3)["05-15"] == 41.0  # (47 + 6 * 40) / 7
        assert len(om.parse_normal_tmax(raw)) == 366

    def test_normal_tmax_rejects_gaps(self):
        raw = {"daily": {"time": ["2001-05-15"], "temperature_2m_max": [42.0]}}
        with pytest.raises(ValueError):
            om.parse_normal_tmax(raw, window_days=0)


class TestRecentConditions:
    RAW = {
        "daily": {
            "time": ["2026-10-25", "2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29"],
            "precipitation_sum": [10.0, 0.0, 2.4, 0.0, 30.0],
            "temperature_2m_mean": [28.0, 29.0, 30.0, 31.0, 99.0],
        },
        "hourly": {"soil_moisture_0_to_7cm": [0.2, 0.18, None]},
    }

    def test_dry_days_before_today_and_latest_soil(self):
        assert om.parse_recent_conditions(self.RAW, date(2026, 10, 29), 2.5) == (3, 0.18)

    def test_past_means_exclude_today(self):
        assert om.parse_past_daily_means(self.RAW, date(2026, 10, 29), days=2) == [30.0, 31.0]


def test_paid_api_key_switches_to_customer_hosts(monkeypatch):
    monkeypatch.delenv("OPEN_METEO_API_KEY", raising=False)
    assert om._with_api_key("https://api.open-meteo.com/v1/forecast", {"a": 1}) == (
        "https://api.open-meteo.com/v1/forecast", {"a": 1})
    monkeypatch.setenv("OPEN_METEO_API_KEY", "k123")
    assert om._with_api_key("https://flood-api.open-meteo.com/v1/flood", {"a": 1}) == (
        "https://customer-flood-api.open-meteo.com/v1/flood", {"a": 1, "apikey": "k123"})
