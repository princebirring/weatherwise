"""Past disasters replayed through the morning warning Graph on the real Bedrock model.

For each event: the backtest's facts for every morning (forecasts as issued then) go to the
same WarningPipeline the live service runs. Writes what one household would have received,
what the Evaluator sent back and why, model calls, tokens, time and cost:
evals/results/AGENT_REPLAYS.md, plus one JSON per event in evals/results/agent_replays/
(the website shows these).

Needs the network, AWS credentials allowed to call the model, and CLIMATE_AGENT_MODEL_ID.

Usage:
    CLIMATE_AGENT_MODEL_ID=us.amazon.nova-pro-v1:0 AWS_REGION=us-east-2 \\
        uv run python -m evals.eval_agent_replays [--event kolhapur_flood_2024_07]
"""

import argparse
import json
import os
from datetime import date
from pathlib import Path

from evals.eval_replays import events
from weatherwise.agents.agent_replay import replay_through_agent
from weatherwise.agents.metering import cost_usd
from weatherwise.agents.orchestrator import bedrock_model
from weatherwise.mcp_server.services import ClimateRiskServices
from weatherwise.rules import message_policy
from weatherwise.weather import ATTRIBUTION

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT_DIR = RESULTS / "agent_replays"
# Which replays go through the agent, and in which of our languages (no Telugu or Malayalam yet).
REPLAYS = {
    "kolhapur_flood_2024_07": "en",
    "vijayawada_flood_2024_08": "en",
    "vidarbha_heat_2026_04": "en",
}


def row(event: dict, result: dict) -> str:
    s = result["summary"]
    lead = f"{s['days_warned_before_event']} days before" if s["days_warned_before_event"] else (
        "no warning before the event" if event.get("event_day") else "-")
    cost = f"${s['cost_usd']}" if s.get("cost_usd") is not None else "n/a"
    return (f"| {event['title']} | {result['language']} | {lead} | {s['mornings_code_flagged']} / "
            f"{s['mornings_with_checked_message']} | {s['messages_delivered']} | {s['drafts_sent_back_by_evaluator']} | "
            f"{s['safe_fallbacks_used']} | {s['model_calls']} | {s['slowest_morning_seconds']} s | {cost} |")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--event", action="append", help="replay id (repeatable); default: all in REPLAYS")
    args = p.parse_args()
    model_id = os.environ.get("CLIMATE_AGENT_MODEL_ID", "")
    model = bedrock_model()
    services = ClimateRiskServices.default()
    chosen = [e for e in events() if e["id"] in (args.event or REPLAYS)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for event in chosen:
        place = services.resolver.resolve(event["lat"], event["lon"], name=event["name"], today=date.today())
        backtest = services.backtest(event["lat"], event["lon"], event["first_day"], event["last_day"], event["name"])
        replay = replay_through_agent(event, backtest, model, message_policy(place.country),
                                      REPLAYS[event["id"]], place.timezone, model_id=model_id)
        result = replay.as_dict()
        s = result["summary"]
        s["cost_usd"] = cost_usd(s["input_tokens"], s["output_tokens"], model_id)
        result["title"] = event["title"]
        (OUT_DIR / f"{event['id']}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
        rows.append(row(event, result))
        print(rows[-1], flush=True)

    RESULTS.joinpath("AGENT_REPLAYS.md").write_text("\n".join([
        "# Past disasters, replayed through the agent",
        "",
        f"Model: `{model_id}` on Amazon Bedrock. Run {date.today()} with `uv run python -m evals.eval_agent_replays`.",
        "Each morning gets only the forecasts issued then. Plain code decides whether to warn; the agent",
        "writes the message; the Evaluator checks it and sends unsafe drafts back; delivery rules decide",
        "what one household would have received (normal warnings 7 AM-8 PM, at most 3 per event, 4 a month).",
        "Every message is in `evals/results/agent_replays/<event>.json`.",
        "",
        "| Event | Language | First warning | Mornings flagged by code / with a checked message | Messages a household got "
        "| Drafts the Evaluator sent back | Safe fallbacks | Model calls | Slowest morning | Model cost |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *rows,
        "",
        f"Prices: `data/bedrock_prices.toml` (AWS Price List API). {ATTRIBUTION}",
        "",
    ]))


if __name__ == "__main__":
    main()
