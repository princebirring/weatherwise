"""AgentCore Runtime entry point (workshop Module 5; plan §8.8.7): one runtime, two modes.

    {"type": "chat", "session_id": "...", "message": "...", "country": "in", "language": "mr",
     "history": [{"role": "user" | "assistant", "text": "..."}, ...]}
        from the WhatsApp / website backend. country comes from resolve_place on the person's
        saved place; language is the person's choice. session_id is a UUID mapped to a
        hashed phone number upstream. The reply is a stream: {"type": "step", "agent", "tool"}
        as each tool starts, then {"type": "reply", ...} once the checked answer is ready.
        history (the earlier turns, kept by the caller) rebuilds the conversation when this
        session's microVM was stopped after sitting idle; a running session ignores it.
    {"type": "warning", "group": {...}}
        from the morning run (EventBridge Scheduler, 3 AM IST: weatherwise/daily_run.py).

Config (env): CLIMATE_AGENT_MODEL_ID (Bedrock model / inference profile), AWS_REGION,
CLIMATE_RISK_MCP_URL (remote MCP server; local stdio if unset), WEATHERWISE_MEMORY_ID (AgentCore
Memory for what the warning agent told each place before; without it, no updates or all-clears).
"""

import os
import queue
import threading
import time
from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from weatherwise.agents.delivery import MemoryLedger, MemoryOutbox
from weatherwise.agents.metering import MeteredModel
from weatherwise.agents.orchestrator import bedrock_model, build_team, climate_risk_client, mcp_tool_caller
from weatherwise.agents.place_memory import AgentCorePlaceMemory
from weatherwise.agents.warning_pipeline import RecipientGroupRun, WarningPipeline, run_report

app = BedrockAgentCoreApp()
_mcp = None
_teams: dict[str, object] = {}  # one team per session inside this runtime microVM
_policies: dict[str, dict] = {}  # message_policy per country, from the MCP server
_memory = None
MAX_SESSIONS_IN_MEMORY = 500    # beyond this, the oldest sessions are dropped (memory guard)
MAX_HISTORY = 12                # earlier turns accepted to rebuild a conversation


def _mcp_client():
    """The one way this runtime reaches climate facts: the Climate Risk MCP server."""
    global _mcp
    if _mcp is None:
        _mcp = climate_risk_client()
        _mcp.start()
    return _mcp


def _policy(country: str) -> dict:
    if country not in _policies:
        _policies[country] = mcp_tool_caller(_mcp_client())("message_policy", {"country_code": country})
    return _policies[country]


def _place_memory():
    global _memory
    memory_id = os.environ.get("WEATHERWISE_MEMORY_ID")
    if _memory is None and memory_id:
        _memory = AgentCorePlaceMemory(memory_id, os.environ.get("AWS_REGION"))
    return _memory


@app.entrypoint
def invoke(payload: dict, context) -> dict | Iterator[dict]:
    kind = payload.get("type", "chat")
    if kind == "chat":
        session = payload.get("session_id") or getattr(context, "session_id", None)
        if not session or len(session) < 33:
            raise ValueError("session_id must be a UUID-like id of 33+ characters")
        message = (payload.get("message") or "").strip()
        if not message or len(message) > 2000:
            raise ValueError("message must be 1-2000 characters")
        history = _history(payload.get("history"))
        team = _teams.get(session)
        if team is None:
            team = build_team(bedrock_model(), _mcp_client().list_tools_sync(),
                              _policy(payload.get("country", "in")), language=payload.get("language"))
            team.remember(history)
            if len(_teams) >= MAX_SESSIONS_IN_MEMORY:
                _teams.pop(next(iter(_teams)))
            _teams[session] = team
        return _chat_stream(team, message)

    if kind == "warning":
        call = mcp_tool_caller(_mcp_client())
        g = payload["group"]
        group = RecipientGroupRun(g["place_name"], g["lat"], g["lon"], g["language"],
                                  g.get("crop"), g.get("water_source"), tuple(g["subscriber_ids"]))
        place = call("resolve_place", {"lat": group.lat, "lon": group.lon})
        # Production: DynamoDB ledger + SQS outbox. In-memory here; the caller persists results.
        ledger, outbox = MemoryLedger(), MemoryOutbox()
        outlook = lambda lat, lon, name: call("hazard_outlook", {"lat": lat, "lon": lon, "place_name": name})  # noqa: E731
        model = MeteredModel(bedrock_model())
        pipeline = WarningPipeline(outlook, model, ledger, outbox, _policy(place["country"]),
                                   memory=_place_memory())
        started = time.monotonic()
        rec = pipeline.run(group, datetime.now(ZoneInfo(place["timezone"])))
        return run_report(rec, outbox, model.usage(), time.monotonic() - started)

    raise ValueError(f"unknown payload type {kind!r}")


def _history(raw) -> list[dict]:
    """The earlier turns the caller sent, checked: words only, nothing the agent could run."""
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_HISTORY:
        raise ValueError(f"history must be a list of at most {MAX_HISTORY} turns")
    turns = []
    for h in raw:
        if not isinstance(h, dict) or h.get("role") not in ("user", "assistant") \
                or not isinstance(h.get("text"), str) or not 0 < len(h["text"]) <= 4000:
            raise ValueError("each history turn needs a role (user or assistant) and 1-4000 characters of text")
        turns.append({"role": h["role"], "text": h["text"]})
    return turns


def _chat_stream(team, message: str):
    """Steps as they happen, then the reply. The team runs in a thread; this generator hands its
    progress to AgentCore, which streams each item to the caller as it is yielded."""
    events: queue.Queue = queue.Queue()

    def run():
        try:
            events.put(("reply", team.reply(message, on_step=lambda step: events.put(("step", step)))))
        except Exception as e:  # re-raised below, in the streaming thread
            events.put(("error", e))

    threading.Thread(target=run, daemon=True).start()
    while True:
        kind, value = events.get()
        if kind == "error":
            raise value
        yield {"type": kind, **value}
        if kind == "reply":
            return


if __name__ == "__main__":
    app.run()
