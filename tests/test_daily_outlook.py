"""The website's 7-day strip: one row per day, middle-run values, and the hazards covering each day."""
from datetime import timedelta

from conftest import ISSUE, forecast, runs_split

from weatherwise.risk.area_scan import AreaWeather, daily_outlook
from weatherwise.risk.models import Hazard, HazardDetection


def weather(tmax, rain, river=None) -> AreaWeather:
    t = forecast(tmax)
    return AreaWeather(
        tmax=t, feels_like_tmax=t, rainfall=forecast(rain),
        normal_tmax={d.strftime("%m-%d"): 38.0 for d in t.dates},
        past_dry_days=0, soil_moisture=None,
        river_discharge=forecast(river) if river else None,
    )


def detection(hazard: Hazard, first: int, last: int) -> HazardDetection:
    return HazardDetection("a", hazard, "warning", ISSUE + timedelta(days=first),
                           ISSUE + timedelta(days=last), first, 0.8)


def test_one_row_per_day_capped_at_seven():
    rows = daily_outlook(weather([40.0] * 10, [0.0] * 10), [])
    assert len(rows) == 7
    assert rows[0]["day"] == ISSUE.isoformat()
    assert rows[0]["normal_tmax_c"] == 38.0


def test_values_are_the_middle_run_and_skip_missing_runs():
    rows = daily_outlook(weather([runs_split(3, 46.0, 41.0) + [None]], [[None] * 9 + [12.0]]), [])
    assert rows[0]["tmax_c"] == 41.0
    assert rows[0]["rain_mm"] == 12.0
    assert rows[0]["river_m3s"] is None


def test_hazards_are_listed_only_on_the_days_they_cover():
    rows = daily_outlook(weather([45.0] * 5, [0.0] * 5, river=[900.0] * 5),
                         [detection(Hazard.HEAT_WAVE, 1, 2)])
    assert [r["hazards"] for r in rows] == [[], ["heat_wave:warning"], ["heat_wave:warning"], [], []]
    assert rows[0]["river_m3s"] == 900.0


def test_rainy_day_uses_the_countrys_line_and_is_unknown_without_rain_data():
    rows = daily_outlook(weather([40.0] * 4, [0.0, 2.4, 2.5, 30.0]), [], rainy_day_mm=2.5)
    assert [r["rainy_day"] for r in rows] == [False, False, True, True]
    assert daily_outlook(weather([40.0] * 2, [[None] * 10, 0.0]), [], rainy_day_mm=2.5)[0]["rainy_day"] is None
    assert daily_outlook(weather([40.0] * 2, [5.0, 5.0]), [])[0]["rainy_day"] is None
