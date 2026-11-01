"""Forecast correction (ours): each model shifted by its own recent error at the place."""
from datetime import date, timedelta

import pytest
from conftest import ISSUE, forecast

from weatherwise.risk.area_scan import AreaWeather, run_checks
from weatherwise.risk.models import Area, Hazard, TerrainZone
from weatherwise.weather import correction as fc
from weatherwise.weather import open_meteo as om


@pytest.fixture
def cfg(rules) -> dict:
    return rules["forecast_correction"]


def errors_for(first: date, days: int, forecast_c: tuple, happened_c: float):
    """Day-ahead forecasts (one value per model) and what happened, for `days` days."""
    day_ahead = {first + timedelta(days=i): forecast_c for i in range(days)}
    observed = {first + timedelta(days=i): happened_c for i in range(days)}
    return day_ahead, observed


class TestLearning:
    def test_shift_is_the_average_error_per_model(self, cfg):
        first, last = fc.training_window(ISSUE, cfg)
        day_ahead, observed = errors_for(first, cfg["training_days"], (41.0, 43.0, 42.0), 42.0)
        assert fc.learn_shifts(day_ahead, observed, first, last, cfg) == (1.0, -1.0, 0.0)

    def test_too_little_history_means_no_shift(self, cfg):
        first, last = fc.training_window(ISSUE, cfg)
        day_ahead, observed = errors_for(first, cfg["min_training_days"] - 1, (40.0,), 42.0)
        assert fc.learn_shifts(day_ahead, observed, first, last, cfg) == (0.0,)

    def test_shift_is_capped(self, cfg):
        assert fc.learn_shift([9.0] * 30, cfg) == cfg["max_shift_c"]
        assert fc.learn_shift([-9.0] * 30, cfg) == -cfg["max_shift_c"]

    def test_warmer_only_when_cooling_is_switched_off(self, cfg):
        assert fc.learn_shift([-1.5] * 30, {**cfg, "allow_cooling": False}) == 0.0
        assert fc.learn_shift([1.5] * 30, {**cfg, "allow_cooling": False}) == 1.5

    def test_learns_only_from_days_already_observed_before_the_morning(self, cfg):
        first, last = fc.training_window(ISSUE, cfg)
        assert last == ISSUE - timedelta(days=cfg["observed_delay_days"])
        assert (last - first).days + 1 == cfg["training_days"]
        # A big error on a day too recent to be known must not count.
        day_ahead, observed = errors_for(first, cfg["training_days"], (40.0,), 40.0)
        day_ahead[last + timedelta(days=1)], observed[last + timedelta(days=1)] = (30.0,), 40.0
        assert fc.learn_shifts(day_ahead, observed, first, last, cfg) == (0.0,)


class TestApplying:
    def test_one_shift_moves_every_run(self):
        out = fc.Correction({"tmax": (1.5,)}, "on").apply("tmax", forecast([40.0, [41.0, None] * 5]))
        assert out.values[0][0] == 41.5 and out.values[1][:2] == (42.5, None)

    def test_one_shift_per_model(self):
        f = forecast([[40.0, 40.0]])
        assert fc.Correction({"tmax": (1.0, -1.0)}, "on").apply("tmax", f).values == ((41.0, 39.0),)

    def test_shift_count_must_match_the_runs(self):
        with pytest.raises(ValueError):
            fc.Correction({"tmax": (1.0, 2.0)}, "on").apply("tmax", forecast([[40.0, 40.0, 40.0]]))

    def test_switched_off_or_unreachable_leaves_the_forecast_alone(self, cfg):
        f = forecast([40.0])
        assert fc.learn({"issued": {}, "observed": {}}, ISSUE, {**cfg, "enabled": False}, ("m",)) is fc.OFF
        assert fc.learn(None, ISSUE, cfg, ("m",)).apply("tmax", f) is f
        assert fc.learn(None, ISSUE, cfg, ("m",)).summary() == {"status": "unavailable", "shift_c": {}}


def test_an_archive_with_too_few_days_says_so(cfg):
    first, _ = fc.training_window(ISSUE, cfg)
    day_ahead, observed = errors_for(first, 3, (40.0,), 42.0)
    series = {n: day_ahead for n in fc.CORRECTED}, {n: observed for n in fc.CORRECTED}
    assert fc.learn_from_series(*series, ISSUE, cfg).summary() == {"status": "no_history", "shift_c": {}}


def test_reads_day_ahead_forecasts_from_the_archive():
    hours = [f"2026-04-0{d}T{h:02d}:00" for d in (1, 2) for h in range(24)]
    raw = {"hourly": {"time": hours,
                      "temperature_2m_previous_day1_a": [30.0] * 24 + [31.0] * 23 + [44.0],
                      "temperature_2m_previous_day1_b": [None] + [30.0] * 47}}
    out = om.parse_day_ahead(raw, "temperature_2m", "max", models=("a", "b"))
    assert out == {date(2026, 4, 1): (30.0, None), date(2026, 4, 2): (44.0, 30.0)}


def test_reads_a_one_model_archive_whose_columns_have_no_model_name():
    """Open-Meteo leaves the model name off when one model is asked for (the live correction)."""
    raw = {"hourly": {"time": [f"2026-04-01T{h:02d}:00" for h in range(24)],
                      "temperature_2m_previous_day1": [30.0] * 23 + [41.0]}}
    assert om.parse_day_ahead(raw, "temperature_2m", "max", models=(om.ENSEMBLE_MODEL,)) == {
        date(2026, 4, 1): (41.0,)}


def test_the_scan_runs_only_enabled_checks_with_their_inputs(rules):
    hot = forecast([45.0] * 5)
    weather = AreaWeather(tmax=hot, feels_like_tmax=hot, rainfall=None,
                          normal_tmax={d.strftime("%m-%d"): 38.0 for d in hot.dates})
    area = Area("a", "Akola", "Akola", TerrainZone.PLAINS, 20.7, 77.0)
    found = {d.hazard for d in run_checks(area, weather, ISSUE, rules).detections}
    assert found == {Hazard.HEAT_WAVE, Hazard.WORK_HEAT}  # no rain, so no rain checks ran
    only_imd = {**rules, "checks": {"enabled": ["heat_wave"]}}
    assert {d.hazard for d in run_checks(area, weather, ISSUE, only_imd).detections} == {Hazard.HEAT_WAVE}
