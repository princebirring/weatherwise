import pytest
from conftest import ISSUE, forecast, runs_split, same_normal

from weatherwise.risk.heat_wave import (
    HEAT_WAVE,
    NONE,
    SEVERE,
    detect_heat_wave,
    detect_work_heat,
    heat_wave_severity,
    work_heat_level,
)
from weatherwise.risk.models import ForecastDataMissing, Hazard, TerrainZone

PLAINS, COAST, HILLS = TerrainZone.PLAINS, TerrainZone.COAST, TerrainZone.HILLS


class TestImdHeatWaveSeverity:
    def test_plains_departure_rule(self, rules):
        assert heat_wave_severity(41.0, 36.5, PLAINS, rules["heat"]) == HEAT_WAVE  # +4.5

    def test_plains_below_base_is_never_a_heat_wave(self, rules):
        assert heat_wave_severity(39.9, 30.0, PLAINS, rules["heat"]) == NONE

    def test_plains_45_counts_even_near_normal(self, rules):
        assert heat_wave_severity(45.0, 43.0, PLAINS, rules["heat"]) == HEAT_WAVE

    def test_plains_severe_by_departure(self, rules):
        assert heat_wave_severity(43.0, 36.55, PLAINS, rules["heat"]) == SEVERE  # +6.45

    def test_plains_severe_at_47(self, rules):
        assert heat_wave_severity(47.0, 44.0, PLAINS, rules["heat"]) == SEVERE

    def test_coast_uses_lower_base(self, rules):
        assert heat_wave_severity(37.5, 33.0, COAST, rules["heat"]) == HEAT_WAVE

    def test_coast_has_no_45_degree_rule(self, rules):
        assert heat_wave_severity(45.0, 42.0, COAST, rules["heat"]) == NONE

    def test_hills_need_departure_too(self, rules):
        assert heat_wave_severity(31.0, 29.0, HILLS, rules["heat"]) == NONE
        assert heat_wave_severity(31.0, 26.0, HILLS, rules["heat"]) == HEAT_WAVE


class TestDetectHeatWave:
    def test_two_day_heat_wave_four_days_ahead(self, rules, akola):
        f = forecast([38, 38, 38, 38, 44, 44, 38])
        found = detect_heat_wave(akola, f, same_normal(f, 39.0), ISSUE, rules["heat"])
        assert len(found) == 1
        d = found[0]
        assert d.hazard is Hazard.HEAT_WAVE
        assert d.severity == "heat_wave"
        assert d.days_ahead == 4
        assert (d.last_day - d.first_day).days == 1

    def test_single_hot_day_does_not_warn(self, rules, akola):
        f = forecast([38, 38, 38, 44, 38, 38, 38])
        assert detect_heat_wave(akola, f, same_normal(f, 39.0), ISSUE, rules["heat"]) == []

    def test_needs_70_percent_of_runs(self, rules, akola):
        f6 = forecast([38, runs_split(6, 44.0, 38.0), runs_split(6, 44.0, 38.0)])
        f7 = forecast([38, runs_split(7, 44.0, 38.0), runs_split(7, 44.0, 38.0)])
        assert detect_heat_wave(akola, f6, same_normal(f6, 39.0), ISSUE, rules["heat"]) == []
        assert len(detect_heat_wave(akola, f7, same_normal(f7, 39.0), ISSUE, rules["heat"])) == 1

    def test_severe_when_runs_agree_on_severe(self, rules, akola):
        f = forecast([38, 47, 47])
        found = detect_heat_wave(akola, f, same_normal(f, 41.0), ISSUE, rules["heat"])
        assert found[0].severity == "severe"

    def test_beyond_seven_days_is_not_warned_yet(self, rules, akola):
        f = forecast([38] * 8 + [44, 44])
        assert detect_heat_wave(akola, f, same_normal(f, 39.0), ISSUE, rules["heat"]) == []

    def test_missing_data_raises_instead_of_all_clear(self, rules, akola):
        f = forecast([38, [44.0] * 3 + [None] * 7, 44])
        with pytest.raises(ForecastDataMissing):
            detect_heat_wave(akola, f, same_normal(f, 39.0), ISSUE, rules["heat"])


class TestWorkHeat:
    """Ours: feels-like heat for outdoor work, in levels set in [work_heat] levels."""

    def test_single_hot_day_warns_kharghar_style(self, rules, kharghar):
        found = detect_work_heat(kharghar, forecast([36, 36, 41, 36]), ISSUE, rules["work_heat"])
        assert len(found) == 1
        assert (found[0].hazard, found[0].severity, found[0].days_ahead) == (Hazard.WORK_HEAT, "take_care", 2)
        assert found[0].evidence["rule"].startswith("ours")

    def test_a_span_takes_its_highest_level(self, rules, kharghar):
        found = detect_work_heat(kharghar, forecast([41, 44, 41, 36]), ISSUE, rules["work_heat"])
        assert [(d.severity, d.days_ahead, (d.last_day - d.first_day).days) for d in found] == [("danger", 0, 2)]

    def test_below_the_lowest_level_is_quiet(self, rules, kharghar):
        assert detect_work_heat(kharghar, forecast([39.9] * 5), ISSUE, rules["work_heat"]) == []

    def test_levels_need_runs_to_agree(self, rules, kharghar):
        split = forecast([runs_split(6, 44.0, 38.0)] * 3)  # 6 of 10 runs: below 70%
        assert detect_work_heat(kharghar, split, ISSUE, rules["work_heat"]) == []

    def test_levels_come_from_the_rules_not_the_code(self, rules, kharghar):
        stricter = {**rules["work_heat"], "levels": [{"name": "danger", "feels_like_c": 45.0}]}
        assert detect_work_heat(kharghar, forecast([44] * 3), ISSUE, stricter) == []
        assert detect_work_heat(kharghar, forecast([46] * 3), ISSUE, stricter)[0].severity == "danger"

    def test_level_of_a_temperature(self, rules):
        assert [work_heat_level(t, rules["work_heat"]) for t in (39.9, 40.0, 42.9, 43.0)] == [
            None, "take_care", "take_care", "danger"]
