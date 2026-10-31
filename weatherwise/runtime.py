"""AgentCore Runtime entry point (workshop Module 5; plan §8.8.7): one runtime, two modes.

    {"type": "chat", "session_id": "...", "message": "...", "country": "in", "language": "mr"}
        from the WhatsApp / website backend. country comes from resolve_place on the person's
        saved place; language is the person's choice. session_id is a UUID mapped to a
        hashed phone number upstream.
    {"type": "warning", "group": {...}}
        from the scheduled Lambda (EventBridge, 6 AM local time).

Config (env): CLIMATE_AGENT_MODEL_ID (Bedrock model / inference profile), AWS_REGION,
CLIMATE_RISK_MCP_URL (remote MCP server; local stdio if unset).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from weatherwise.agents.delivery import MemoryLedger, MemoryOutbox
from weatherwise.agents.orchestrator import bedrock_model, build_team, climate_risk_client, mcp_tool_caller
from weatherwise.agents.warning_pipeline import RecipientGroupRun, WarningPipeline

app = BedrockAgentCoreApp()
_mcp = None
_teams: dict[str, object] = {}  # one team per session inside this runtime microVM
_policies: dict[str, dict] = {}  # message_policy per country, from the MCP server
MAX_SESSIONS_IN_MEMORY = 500    # beyond this, the oldest sessions are dropped (memory guard)


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


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    kind = payload.get("type", "chat")
    if kind == "chat":
        session = payload.get("session_id") or getattr(context, "session_id", None)
        if not session or len(session) < 33:
            raise ValueError("session_id must be a UUID-like id of 33+ characters")
        message = (payload.get("message") or "").strip()
        if not message or len(message) > 2000:
            raise ValueError("message must be 1-2000 characters")
        team = _teams.get(session)
        if team is None:
            team = build_team(bedrock_model(), _mcp_client().list_tools_sync(),
                              _policy(payload.get("country", "in")), language=payload.get("language"))
            if len(_teams) >= MAX_SESSIONS_IN_MEMORY:
                _teams.pop(next(iter(_teams)))
            _teams[session] = team
        return team.reply(message)

    if kind == "warning":
        call = mcp_tool_caller(_mcp_client())
        g = payload["group"]
        group = RecipientGroupRun(g["place_name"], g["lat"], g["lon"], g["language"],
                                  g.get("crop"), g.get("water_source"), tuple(g["subscriber_ids"]))
        place = call("resolve_place", {"lat": group.lat, "lon": group.lon})
        # Production: DynamoDB ledger + SQS outbox. In-memory here; the caller persists results.
        ledger, outbox = MemoryLedger(), MemoryOutbox()
        outlook = lambda lat, lon, name: call("hazard_outlook", {"lat": lat, "lon": lon, "place_name": name})  # noqa: E731
        pipeline = WarningPipeline(outlook, bedrock_model(), ledger, outbox, _policy(place["country"]))
        rec = pipeline.run(group, datetime.now(ZoneInfo(place["timezone"])))
        return {"hazard_kind": rec.hazard_kind, "used_fallback": rec.used_fallback,
                "rules_version_mismatch": rec.rules_version_mismatch,
                "violations": rec.violations, "deliveries": rec.deliveries, "outbox": outbox.messages}

    raise ValueError(f"unknown payload type {kind!r}")


if __name__ == "__main__":
    app.run()
