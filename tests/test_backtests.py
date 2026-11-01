"""Headline backtests replayed offline from saved inputs (plan §12, §13, §16).

They pin today's measured results, so any change to rules or code that alters what we
would have sent in a real disaster is noticed in review.
"""

import copy
import gzip
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from weatherwise.backtest.backtest import run_backtest
from weatherwise.backtest.verification import verify
from weatherwise.places.resolve import PlaceContext
from weatherwise.rules import load_rules

SNAPSHOTS = Path(__file__).parent / "backtest_snapshots"


def replay(snapshot_id: str, change=None):
    """Replay a saved event; change(rules) can switch rules off to compare."""
    path = SNAPSHOTS / f"{snapshot_id}.json.gz"
    if not path.exists():
        pytest.skip("no snapshot; run scripts/backtest.py --headline --save-snapshots")
    with gzip.open(path, "rt") as f:
        saved = json.load(f)
    place = PlaceContext.from_summary(saved["place"])
    rules = copy.deepcopy(load_rules(place.country))
    if change:
        change(rules)
    bt = run_backtest(place, date.fromisoformat(saved["first_day"]),
                      date.fromisoformat(saved["last_day"]), saved["inputs"], rules)
    return bt, verify(bt)


def old_flood_signals(rules):
    """The flood guide before Oct 2026: only very heavy rain or the river started PREPARE."""
    rules["flood_guide"]["prepare_signals"] = ["very_heavy_rain", "river_flood"]


def guide_days(bt) -> list[str]:
    return [d.day.isoformat() for d in bt.days if d.flood_guide_mode]


def test_kolhapur_flood_2024_caught_9_days_ahead_without_false_alarms():
    bt, v = replay("kolhapur_flood_2024_07")
    guide = v["scores"]["flood_guide"]
    assert bt.mode == "as_issued"
    assert bt.flood_level_m3s == pytest.approx(1320.5)  # river history before 2024 only
    assert guide["event_lead_days"] == [("2024-07-26", 9)]  # the reported danger-mark day
    assert (guide["hits"], guide["misses"], guide["false_alarms"]) == (1, 0, 0)
    assert all(d.flood_guide_mode != "urgent" for d in bt.days)  # model data never says "move now"
    # Heavy rain two days running upstream in the Ghats starts it on Jul 17; it stays on through
    # the flood, never switching off on the quiet forecasts of Jul 22-25.
    on = guide_days(bt)
    assert on[0] == "2024-07-17" and "2024-07-26" in on
    assert bt.days[2].flood_guide_reasons[0].startswith("heavy_rain_days_in_a_row: heavy_rain heavy at Gaganbawda")
    first = date.fromisoformat(on[0])
    assert on == [(first + timedelta(days=i)).isoformat() for i in range(len(on))]  # one unbroken run


def test_kolhapur_old_signals_started_only_when_the_river_did():
    bt, v = replay("kolhapur_flood_2024_07", old_flood_signals)
    assert guide_days(bt)[0] == "2024-07-21" and v["scores"]["flood_guide"]["event_lead_days"] == [("2024-07-26", 5)]


def test_vijayawada_2024_rain_flood_caught_before_the_extreme_rain():
    bt, v = replay("vijayawada_flood_2024_08")
    on = guide_days(bt)
    assert on[0] == "2024-08-29"  # two days before 186 mm fell on Aug 31
    assert bt.days[5].flood_guide_reasons[0].startswith("unusual_rain:")
    guide = v["scores"]["flood_guide"]
    assert (guide["hits"], guide["misses"], guide["false_alarms"]) == (1, 0, 0)
    assert all(d.flood_guide_mode != "urgent" for d in bt.days)


def test_vijayawada_old_signals_never_started_the_guide():
    """The national mm line was never forecast in the ~25 km square: the old rules stayed silent."""
    bt, v = replay("vijayawada_flood_2024_08", old_flood_signals)
    assert guide_days(bt) == [] and v["scores"]["flood_guide"]["misses"] == 2  # Aug 30-Sep 1, Sep 3


def test_vidarbha_heat_2026_scores():
    bt, v = replay("vidarbha_heat_2026_04")
    s = v["scores"]
    assert bt.mode == "as_issued"
    assert (s["excess_heat"]["hits"], s["excess_heat"]["misses"], s["excess_heat"]["false_alarms"]) == (8, 4, 1)
    assert (s["work_heat:take_care"]["hits"], s["work_heat:take_care"]["false_alarms"]) == (15, 6)
    assert (s["work_heat:danger"]["hits"], s["work_heat:danger"]["false_alarms"]) == (3, 7)
    # Honest limit: the IMD station rule never fires on gridded data here (station 46.9 C,
    # grid ~43.6 C), which is why the work-heat levels and Excess Heat Factor exist.
    assert s["heat_wave"]["hits"] == 0


def test_vidarbha_forecast_correction_catches_more_unusual_heat():
    _, without = replay("vidarbha_heat_2026_04",
                        lambda r: r["forecast_correction"].update(enabled=False))
    _, with_it = replay("vidarbha_heat_2026_04")
    assert without["scores"]["excess_heat"]["hits"] == 7 and with_it["scores"]["excess_heat"]["hits"] == 8
    assert with_it["scores"]["excess_heat"]["false_alarms"] < without["scores"]["excess_heat"]["false_alarms"]


def test_a_check_switched_off_never_warns():
    def off(rules):
        rules["checks"]["enabled"] = [c for c in rules["checks"]["enabled"] if c != "work_heat"]
    bt, v = replay("vidarbha_heat_2026_04", off)
    assert not any(w["hazard"] == "work_heat" for d in bt.days for w in d.warnings)
    assert v["scores"]["work_heat:take_care"]["hits"] == 0


def test_kharghar_2023_conditions_met_on_the_day_imd_was_silent():
    bt, v = replay("kharghar_heat_2023_04")
    assert bt.mode == "conditions_only"
    day = v["conditions_met"]["2023-04-16"]
    assert "heat_wave" in day and "excess_heat" in day and "work_heat:take_care" in day


def test_no_lead_time_claims_before_the_forecast_archive():
    bt, _ = replay("kharghar_heat_2023_04")
    assert all(not d.warnings for d in bt.days)
