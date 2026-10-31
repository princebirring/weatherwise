"""Developer tool: calls ClimateRiskServices in-process (the same code the MCP server runs).
Production callers (agents, scheduled pipeline) go through the MCP server.

Backtest any place and dates, or the headline events in evals/headline_events.toml.

Usage:
    uv run python scripts/backtest.py --lat 16.70 --lon 74.24 --from 2024-07-15 --to 2024-08-05
    uv run python scripts/backtest.py --headline [--save-snapshots]   # evals/headline_events.toml

--save-snapshots stores every raw input (gzipped) under tests/backtest_snapshots/ so the
test suite replays the headline events offline.
"""

import argparse
import gzip
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tomllib  # noqa: E402

from weatherwise.backtest.backtest import gather_inputs, run_backtest  # noqa: E402
from weatherwise.backtest.verification import verify  # noqa: E402
from weatherwise.mcp_server.services import ClimateRiskServices  # noqa: E402
from weatherwise.rules import load_rules  # noqa: E402
from weatherwise.weather import ATTRIBUTION  # noqa: E402

SNAPSHOT_DIR = ROOT / "tests" / "backtest_snapshots"
HEADLINE_EVENTS = ROOT / "evals" / "headline_events.toml"


def run_one(services: ClimateRiskServices, lat, lon, first: date, last: date, name, snapshot_id=None):
    place = services.resolver.resolve(lat, lon, name=name, today=date.today())
    rules = load_rules(place.country)
    weather = services.resolver.weather(place.timezone)
    inputs = gather_inputs(place, first, last, weather, rules)
    if snapshot_id:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"place": place.summary(), "first_day": str(first), "last_day": str(last),
                   "inputs": inputs}
        with gzip.open(SNAPSHOT_DIR / f"{snapshot_id}.json.gz", "wt") as f:
            json.dump(payload, f, default=str)
    return place, run_backtest(place, first, last, inputs, rules)


def show(title, place, bt) -> None:
    v = verify(bt)
    print(f"== {title}  [{bt.mode}]  ({ATTRIBUTION})")
    print(f"   {place.name}, {place.admin.district}, {place.admin.state}; terrain {place.terrain.value}; "
          f"flood level {bt.flood_level_m3s}")
    if "scores" in v:
        for hazard, s in v["scores"].items():
            if s["hits"] or s["misses"] or s["false_alarms"]:
                print(f"   {hazard:<16} hits {s['hits']:>2}  misses {s['misses']:>2}  false alarms "
                      f"{s['false_alarms']:>2}  POD {s['pod']}  FAR {s['far']}  "
                      f"events (start, lead days) {s['event_lead_days']}")
        print(f"   heat Brier score, 1 day ahead: {v['heat_brier_score_1_day_ahead']}")
    else:
        print(f"   {v['note']}")
        for day, events in v["conditions_met"].items():
            print(f"   {day}: {', '.join(events)}")
    for note in bt.notes:
        print(f"   note: {note}")
    print()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--from", dest="first")
    p.add_argument("--to", dest="last")
    p.add_argument("--name")
    p.add_argument("--headline", action="store_true")
    p.add_argument("--save-snapshots", action="store_true")
    args = p.parse_args()
    services = ClimateRiskServices.default()

    if args.headline:
        events = tomllib.loads(HEADLINE_EVENTS.read_text())["replay"]
        for r in events:
            rid = r["id"]
            place, bt = run_one(services, r["lat"], r["lon"], date.fromisoformat(r["first_day"]),
                                date.fromisoformat(r["last_day"]), r["name"],
                                rid if args.save_snapshots else None)
            show(f"{r['title']} -- reported: {r['reported']}", place, bt)
    else:
        place, bt = run_one(services, args.lat, args.lon, date.fromisoformat(args.first),
                            date.fromisoformat(args.last), args.name)
        show("Backtest", place, bt)


if __name__ == "__main__":
    main()
