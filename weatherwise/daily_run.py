"""This morning, the agent: a warning run for every place in data/daily_watch.toml.

In production EventBridge Scheduler starts this as a one-off ECS task each morning. Each place
is one call to the agent on AgentCore Runtime (the morning warning Graph: plain-code risk scan,
the agent writes, the Evaluator checks). The results go to S3, where the website reads them
(GET /api/daily):

    daily/<date>.json   every place's run (message, what the Evaluator sent back, calls, time)
    daily/latest.json   the same, for the newest run
    daily/index.json    one summary line per morning, newest first

Nothing is sent to anyone: these places have no subscribers. A failed place (for example the
weather service's daily limit) is recorded as failed, never hidden. The agent remembers what it
told each place (AgentCore Memory; locally <out>/memory.json), so the next morning it writes an
update, or an all-clear when the risk has eased.

Usage:
    uv run python -m weatherwise.daily_run                 # AgentCore + S3 (the scheduled task)
    uv run python -m weatherwise.daily_run --local out/    # in-process Graph, results in out/
    uv run python -m weatherwise.daily_run --local out/ --only Akola --only Kolhapur
"""

import argparse
import json
import os
import time
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from weatherwise.agents.metering import cost_usd

WATCH_FILE = Path(__file__).resolve().parent.parent / "data" / "daily_watch.toml"
DEMO_SUBSCRIBER = "watch-demo"
PARALLEL = 4
INDEX_DAYS = 60


def watched_places() -> list[dict]:
    return tomllib.loads(WATCH_FILE.read_text())["place"]


def group_payload(place: dict) -> dict:
    return {"place_name": place["name"], "lat": place["lat"], "lon": place["lon"],
            "language": place["language"], "subscriber_ids": [DEMO_SUBSCRIBER]}


def via_agentcore(client, runtime_arn: str):
    from weatherwise.api.agentcore import invoke_runtime

    def run(place: dict) -> dict:
        return invoke_runtime(client, runtime_arn, str(uuid4()), {"type": "warning", "group": group_payload(place)})
    return run


def in_process(memory_file: Path):
    """The same Graph without AgentCore, for development (facts from in-process services)."""
    from weatherwise.agents.delivery import MemoryLedger, MemoryOutbox
    from weatherwise.agents.metering import MeteredModel
    from weatherwise.agents.orchestrator import bedrock_model
    from weatherwise.agents.place_memory import LocalPlaceMemory
    from weatherwise.agents.warning_pipeline import RecipientGroupRun, WarningPipeline, run_report
    from weatherwise.mcp_server.services import ClimateRiskServices
    from weatherwise.rules import message_policy

    services = ClimateRiskServices.default()
    memory = LocalPlaceMemory(memory_file)

    def run(place: dict) -> dict:
        g = group_payload(place)
        resolved = services.resolve_place(g["lat"], g["lon"])
        group = RecipientGroupRun(g["place_name"], g["lat"], g["lon"], g["language"], None, None,
                                  tuple(g["subscriber_ids"]))
        model, outbox = MeteredModel(bedrock_model()), MemoryOutbox()
        pipeline = WarningPipeline(lambda lat, lon, name: services.hazard_outlook(lat, lon, name), model,
                                   MemoryLedger(), outbox, message_policy(resolved["country"]), memory=memory)
        started = time.monotonic()
        rec = pipeline.run(group, datetime.now(ZoneInfo(resolved["timezone"])))
        return run_report(rec, outbox, model.usage(), time.monotonic() - started)
    return run


def run_all(run_place, places: list[dict], model_id: str) -> dict:
    started_at = datetime.now(timezone.utc)

    def one(place: dict) -> dict:
        t0 = time.monotonic()
        try:
            return {"place": place, "ok": True, **run_place(place), "wall_seconds": round(time.monotonic() - t0, 2)}
        except Exception as e:  # recorded, never hidden
            return {"place": place, "ok": False, "error": f"{type(e).__name__}: {e}"[:300],
                    "wall_seconds": round(time.monotonic() - t0, 2)}

    with ThreadPoolExecutor(PARALLEL) as pool:
        results = list(pool.map(one, places))
    finished_at = datetime.now(timezone.utc)
    ok = [r for r in results if r["ok"]]
    tokens_in = sum(r.get("input_tokens", 0) for r in ok)
    tokens_out = sum(r.get("output_tokens", 0) for r in ok)
    flagged = [r for r in ok if r.get("hazard_kind")]
    kinds = [r.get("hazard_kind") for r in flagged]
    return {
        "run_date": started_at.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat(),
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "model_id": model_id,
        "summary": {
            "places": len(results), "finished": len(ok), "failed": len(results) - len(ok),
            "warnings_written": len(flagged) - kinds.count("all_clear"),
            "updates_of_earlier_warnings": sum(bool(r.get("earlier_warnings")) and r["hazard_kind"] != "all_clear"
                                               for r in flagged),
            "all_clears": kinds.count("all_clear"),
            "drafts_sent_back_by_evaluator": sum(len(r.get("evaluator_sent_back", [])) for r in flagged),
            "safe_fallbacks_used": sum(bool(r.get("used_fallback")) for r in flagged),
            "model_calls": sum(r.get("model_calls", 0) for r in ok),
            "input_tokens": tokens_in, "output_tokens": tokens_out,
            "model_cost_usd": cost_usd(tokens_in, tokens_out, model_id),
            "slowest_place_seconds": max((r["wall_seconds"] for r in results), default=0.0),
            "total_seconds": round((finished_at - started_at).total_seconds(), 1),
        },
        "places": results,
    }


def index_line(run: dict) -> dict:
    return {"run_date": run["run_date"], "started_at": run["started_at"], **run["summary"]}


def save_s3(run: dict, bucket: str) -> None:
    import boto3

    s3 = boto3.client("s3")
    body = json.dumps(run, ensure_ascii=False).encode()
    for key in (f"daily/{run['run_date']}.json", "daily/latest.json"):
        s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    try:
        index = json.loads(s3.get_object(Bucket=bucket, Key="daily/index.json")["Body"].read())
    except s3.exceptions.NoSuchKey:
        index = []
    index = [index_line(run)] + [x for x in index if x["run_date"] != run["run_date"]]
    s3.put_object(Bucket=bucket, Key="daily/index.json", ContentType="application/json",
                  Body=json.dumps(index[:INDEX_DAYS]).encode())


def save_local(run: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    body = json.dumps(run, ensure_ascii=False, indent=1)
    for name in (f"{run['run_date']}.json", "latest.json"):
        (out / name).write_text(body)
    path = out / "index.json"
    index = json.loads(path.read_text()) if path.exists() else []
    index = [index_line(run)] + [x for x in index if x["run_date"] != run["run_date"]]
    path.write_text(json.dumps(index[:INDEX_DAYS], indent=1))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--local", type=Path, help="run the Graph in-process and write results here")
    p.add_argument("--only", action="append", help="run just these places (repeatable)")
    args = p.parse_args()
    places = [x for x in watched_places() if not args.only or x["name"] in args.only]
    model_id = os.environ.get("CLIMATE_AGENT_MODEL_ID", "")
    if args.local:
        run = run_all(in_process(args.local / "memory.json"), places, model_id)
        save_local(run, args.local)
    else:
        from weatherwise.api.agentcore import runtime_client

        run = run_all(via_agentcore(runtime_client(), os.environ["WEATHERWISE_AGENT_RUNTIME_ARN"]),
                      places, model_id)
        save_s3(run, os.environ["WEATHERWISE_CACHE_BUCKET"])
    print(json.dumps(index_line(run)))


if __name__ == "__main__":
    main()
