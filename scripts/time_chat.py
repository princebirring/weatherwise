"""Developer tool: where does one chat answer's time go?

Runs one realistic chat turn (a Marathi heat question for Akola) through the real agent team and
the real Climate Risk MCP server (live forecasts), with a scripted model in place of Bedrock. It
splits the time into our own work (tools, forecasts, agent set-up) and model calls, and counts
how many model calls one answer needs.

Usage:
    uv run python scripts/time_chat.py                      # scripted model, Tone check on
    uv run python scripts/time_chat.py --no-tone            # the same without the Tone check
    uv run python scripts/time_chat.py --model-seconds 2.5  # pretend each model call takes 2.5 s
    CLIMATE_AGENT_MODEL_ID=... AWS_REGION=... uv run python scripts/time_chat.py --bedrock
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.scripted_model import ScriptedModel  # noqa: E402
from weatherwise.agents.orchestrator import (  # noqa: E402
    bedrock_model,
    build_team,
    climate_risk_client,
    mcp_tool_caller,
)

PLACE = {"name": "Akola", "lat": 20.70957, "lon": 76.9981}
QUESTION = "उद्या अकोल्यात खूप ऊन असेल का?"
REPLY = "उद्या उष्णतेची काळजी घ्या. सकाळी लवकर काम करा, सावलीत विश्रांती घ्या. उष्माघात झाल्यास 108 वर फोन करा."
APPROVE = {"decision": "approve", "reason": "fine"}


def scripted_turn() -> list:
    """What a model typically does for this question: warnings, outlook, hand-off, reply."""
    at = {"lat": PLACE["lat"], "lon": PLACE["lon"]}
    return [
        ("tool", "official_alerts", at),
        ("tool", "hazard_outlook", {**at, "place_name": PLACE["name"]}),
        ("tool", "warning_agent", {"request": "Heat advice for a farmer in Akola (20.71, 77.00), in Marathi."}),
        ("tool", "hazard_outlook", {**at, "place_name": PLACE["name"]}),  # the specialist checks the facts
        REPLY,  # the specialist's message
        REPLY,  # the Orchestrator's reply
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-tone", action="store_true", help="switch the Tone check off")
    parser.add_argument("--model-seconds", type=float, default=0.0, help="pretend response time per model call")
    parser.add_argument("--bedrock", action="store_true", help="use the real model from CLIMATE_AGENT_MODEL_ID")
    args = parser.parse_args()

    started = time.monotonic()
    client = climate_risk_client()
    client.start()
    tools = client.list_tools_sync()
    policy = mcp_tool_caller(client)("message_policy", {"country_code": "in"})
    mcp_seconds = time.monotonic() - started

    if args.bedrock:
        model = tone_model = bedrock_model()
    else:
        model = ScriptedModel(scripted_turn(), args.model_seconds)
        tone_model = ScriptedModel([APPROVE] * 50, args.model_seconds)

    started = time.monotonic()
    team = build_team(model, tools, policy, language="mr", tone_model=tone_model, with_tone_check=not args.no_tone)
    build_seconds = time.monotonic() - started

    message = (f"[System: the person's saved place is {PLACE['name']} (lat {PLACE['lat']}, "
               f"lon {PLACE['lon']}); it is already confirmed.]\n{QUESTION}")
    started = time.monotonic()
    out = team.reply(message)
    turn_seconds = time.monotonic() - started
    client.stop(None, None, None)

    tool_seconds = sum(s["seconds"] for s in out["steps"])
    print(f"Start MCP server + list tools : {mcp_seconds:6.1f} s  (once per server start)")
    print(f"Build the agent team         : {build_seconds:6.1f} s  (once per chat session)")
    print(f"One chat turn                : {turn_seconds:6.1f} s")
    for s in out["steps"]:
        print(f"   {s['agent']:<18} {s['tool']:<18} {s['status']:<8} {s['seconds']:6.2f} s")
    if not args.bedrock:
        calls = model.calls + tone_model.calls
        print(f"Model calls                  : {model.calls} answer + {tone_model.calls} Tone check = {calls}")
        print(f"   of which pretend model time: {calls * args.model_seconds:6.1f} s")
    print(f"Orchestrator tool time (incl. specialists) : {tool_seconds:6.1f} s")
    print(f"Reply ({'fallback' if out['used_fallback'] else 'model'}): {out['text'][:120]}")
    if out["violations"]:
        print(f"Evaluator flagged: {out['violations']}")


if __name__ == "__main__":
    main()
