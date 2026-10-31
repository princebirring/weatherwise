"""Excess Heat Factor (ours; Nairn & Fawcett 2015): self-calibrating to each place's climate."""

import pytest
from conftest import ISSUE, forecast, runs_split

from weatherwise.risk.heat_wave import detect_excess_heat, excess_heat_factor, heat_climate
from weatherwise.risk.models import ForecastDataMissing, Hazard

CLIMATE = {"t95": 35.0, "ehf_severe": 4.0}


def test_ehf_formula():
    # 3-day mean 37 is 2 above T95 (35) and 7 above the previous 30 days (30): 2 * 7 = 14.
    assert excess_heat_factor([37, 37, 37], [30.0] * 30, 35.0) == pytest.approx(14.0)


def test_ehf_negative_when_below_local_heat_line():
    assert excess_heat_factor([33, 33, 33], [30.0] * 30, 35.0) < 0


def test_acclimatised_heat_is_not_amplified():
    # Hot, but no hotter than the last month: acclimatisation factor floors at 1.
    assert excess_heat_factor([36, 36, 36], [37.0] * 30, 35.0) == pytest.approx(1.0)


def test_climate_baseline_from_history():
    means = [30.0] * 360 + [38.0] * 5 + [30.0] * 30
    clim = heat_climate(means, heat_percentile=95, severe_percentile=85)
    assert clim["t95"] == 30.0
    assert clim["ehf_severe"] > 0


def test_detects_heat_above_local_line(rules, akola):
    f = forecast([36.5, 37.0, 37.5, 37.0, 36.0])
    found = detect_excess_heat(akola, f, [30.0] * 30, CLIMATE, ISSUE, rules["excess_heat"])
    assert found and found[0].hazard is Hazard.EXCESS_HEAT
    assert found[0].severity == "severe"
    assert found[0].evidence["rule"].startswith("ours")


def test_needs_agreement(rules, akola):
    f = forecast([runs_split(6, 38.0, 30.0)] * 5)
    assert detect_excess_heat(akola, f, [30.0] * 30, CLIMATE, ISSUE, rules["excess_heat"]) == []


def test_normal_weather_is_quiet(rules, akola):
    f = forecast([31.0] * 6)
    assert detect_excess_heat(akola, f, [30.0] * 30, CLIMATE, ISSUE, rules["excess_heat"]) == []


def test_needs_30_days_of_history(rules, akola):
    with pytest.raises(ForecastDataMissing):
        detect_excess_heat(akola, forecast([38.0] * 5), [30.0] * 10, CLIMATE, ISSUE,
                           rules["excess_heat"])
