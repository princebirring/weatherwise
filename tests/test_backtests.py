"""Headline backtests replayed offline from saved inputs (plan §12, §13, §16).

They pin today's measured results, so any change to rules or code that alters what we
would have sent in a real disaster is noticed in review.
"""

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


def replay(snapshot_id: str):
    path = SNAPSHOTS / f"{snapshot_id}.json.gz"
    if not path.exists():
        pytest.skip("no snapshot; run scripts/backtest.py --headline --save-snapshots")
    with gzip.open(path, "rt") as f:
        saved = json.load(f)
    place = PlaceContext.from_summary(saved["place"])
    rules = load_rules(place.country)
    bt = run_backtest(place, date.fromisoformat(saved["first_day"]),
                      date.fromisoformat(saved["last_day"]), saved["inputs"], rules)
    return bt, verify(bt)


def test_kolhapur_flood_2024_caught_5_days_ahead_without_false_alarms():
    bt, v = replay("kolhapur_flood_2024_07")
    river = v["scores"]["river_flood"]
    assert bt.mode == "as_issued"
    assert bt.flood_level_m3s == pytest.approx(1320.5)  # river history before 2024 only
    assert river["event_lead_days"] == [("2024-07-26", 5)]  # the reported danger-mark day
    assert (river["hits"], river["misses"], river["false_alarms"]) == (1, 0, 0)
    assert all(d.flood_guide_mode != "urgent" for d in bt.days)  # model data never says "move now"
    # The guide starts Jul 21 and stays on through the flood: no switching off on Jul 22-25.
    on = [d.day.isoformat() for d in bt.days if d.flood_guide_mode]
    assert on[0] == "2024-07-21" and "2024-07-26" in on
    first = date.fromisoformat(on[0])
    assert on == [(first + timedelta(days=i)).isoformat() for i in range(len(on))]  # one unbroken run


def test_vidarbha_heat_2026_excess_heat_scores():
    bt, v = replay("vidarbha_heat_2026_04")
    ehf = v["scores"]["excess_heat"]
    assert bt.mode == "as_issued"
    assert ehf["pod"] == pytest.approx(0.58) and ehf["far"] == pytest.approx(0.22)
    # Honest limit: the IMD station rule never fires on gridded data here (station 46.9 C,
    # grid ~43.6 C), which is why the self-calibrating Excess Heat Factor exists.
    assert v["scores"]["heat_wave"]["hits"] == 0


def test_kharghar_2023_conditions_met_on_the_day_imd_was_silent():
    bt, v = replay("kharghar_heat_2023_04")
    assert bt.mode == "conditions_only"
    assert "heat_wave" in v["conditions_met"]["2023-04-16"]
    assert "excess_heat" in v["conditions_met"]["2023-04-16"]


def test_no_lead_time_claims_before_the_forecast_archive():
    bt, _ = replay("kharghar_heat_2023_04")
    assert all(not d.warnings for d in bt.days)
