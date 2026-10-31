"""Developer tool: calls ClimateRiskServices in-process (the same code the MCP server runs).
Production callers (agents, scheduled pipeline) go through the MCP server.

Today's real hazard outlook for any points (default: the test places).

Usage:
    uv run python scripts/scan_today.py                       # test places
    uv run python scripts/scan_today.py --lat 25.59 --lon 85.14 --name Patna
"""

import argparse
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from weatherwise.mcp_server.services import ClimateRiskServices  # noqa: E402
from weatherwise.weather import ATTRIBUTION  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--name")
    args = p.parse_args()
    if args.lat is not None:
        points = [(args.name or f"{args.lat},{args.lon}", args.lat, args.lon)]
    else:
        places = tomllib.loads((ROOT / "tests" / "fixtures" / "places.toml").read_text())["place"]
        points = [(x["id"].title(), x["lat"], x["lon"]) for x in places]

    services = ClimateRiskServices.default()
    print(ATTRIBUTION)
    for name, lat, lon in points:
        o = services.hazard_outlook(lat, lon, name)
        pl = o["place"]
        print(f"\n== {pl['name']} ({pl['district']}, {pl['state']}; {pl['terrain']}; "
              f"large river: {pl['large_river_nearby']}; cell {pl['forecast_cell']}) on {o['issue_date']}")
        if o["data_missing"]:
            print(f"   DATA MISSING (not 'no risk'): {o['data_missing']}")
        for d in o["detections"]:
            print(f"   -> {d['hazard'].upper()} [{d['severity']}] {d['first_day']}..{d['last_day']}, "
                  f"{d['days_ahead']} days ahead, {d['agreement']:.0%} of runs agree")
        if o["flood_guide"]["mode"]:
            print(f"   FLOOD GUIDE: {o['flood_guide']['mode'].upper()}: {'; '.join(o['flood_guide']['reasons'])}")
        if not o["detections"]:
            print("   -> No hazard detected.")


if __name__ == "__main__":
    main()
