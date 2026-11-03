"""A past disaster, replayed through the morning warning Graph.

Each replay morning gets the facts the 6 AM scan would have had then (forecasts as issued,
from the backtest tool) and runs the same WarningPipeline the live service runs: code decides
whether to warn, the agent writes the message, the Evaluator checks it, delivery rules decide
what one household would have received. One ledger runs across the whole replay, so the
per-event limit applies as it would have.
"""

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from datetime import time as clock
from zoneinfo import ZoneInfo

from weatherwise.agents.delivery import DeliveryRules, MemoryLedger, MemoryOutbox
from weatherwise.agents.metering import MeteredModel
from weatherwise.agents.warning_pipeline import RecipientGroupRun, WarningPipeline

HOUSEHOLD = "replay-household"


def morning_outlooks(backtest: dict) -> list[dict]:
    """hazard_outlook-shaped facts for each replay morning, from the MCP backtest tool's reply."""
    return [{"place": backtest["place"], "covered": True, "issue_date": d["day"],
             "detections": d["detections"],
             "flood_guide": {"mode": d["flood_guide"], "reasons": d["flood_guide_reasons"]},
             "data_missing": d.get("data_missing", []), "rules_version": backtest.get("rules_version"),
             "replay": True}
            for d in backtest["timeline"]]


@dataclass
class ReplayMorning:
    day: str
    code_flagged: str | None          # what plain code decided: "flood", "heat_dry" or None (quiet)
    what_happened: list[str]
    message: str | None = None        # what the household would have read (after the final gate)
    draft: str | None = None          # the agent's last draft
    used_fallback: bool = False
    model_error: str | None = None
    evaluator_sent_back: list[list[str]] = field(default_factory=list)
    delivered: str | None = None      # "send", "defer", "skip" or None (nothing to send)
    seconds: float = 0.0
    usage: dict = field(default_factory=dict)


@dataclass
class AgentReplay:
    event_id: str
    place: dict
    language: str
    model_id: str
    event_day: str | None
    mornings: list[ReplayMorning]

    def summary(self) -> dict:
        flagged = [m for m in self.mornings if m.code_flagged]
        written = [m for m in flagged if m.message]
        before = [m for m in flagged if self.event_day and m.day < self.event_day]
        first = min((m.day for m in before), default=None)
        return {
            "mornings": len(self.mornings),
            "mornings_code_flagged": len(flagged),
            "mornings_with_checked_message": len(written),
            "messages_delivered": sum(m.delivered == "send" for m in self.mornings),
            "first_warning_day": first,
            "days_warned_before_event": (date.fromisoformat(self.event_day) - date.fromisoformat(first)).days
            if first else None,
            "drafts_sent_back_by_evaluator": sum(len(m.evaluator_sent_back) for m in self.mornings),
            "safe_fallbacks_used": sum(m.used_fallback for m in flagged),
            "model_failures": sum(m.model_error is not None for m in flagged),
            "model_calls": sum(m.usage.get("model_calls", 0) for m in self.mornings),
            "input_tokens": sum(m.usage.get("input_tokens", 0) for m in self.mornings),
            "output_tokens": sum(m.usage.get("output_tokens", 0) for m in self.mornings),
            "slowest_morning_seconds": max((m.seconds for m in flagged), default=0.0),
        }

    def as_dict(self) -> dict:
        return {**{k: v for k, v in asdict(self).items() if k != "mornings"},
                "summary": self.summary(), "mornings": [asdict(m) for m in self.mornings]}


def replay_through_agent(event: dict, backtest: dict, model, policy: dict, language: str,
                         timezone: str, model_id: str = "",
                         make_pipeline: Callable[..., WarningPipeline] = WarningPipeline) -> AgentReplay:
    """event: a [[replay]] row from headline_events.toml; backtest: the MCP backtest tool's reply."""
    meter = model if isinstance(model, MeteredModel) else MeteredModel(model)
    ledger, outbox = MemoryLedger(), MemoryOutbox()
    group = RecipientGroupRun(event["name"], event["lat"], event["lon"], language, None, None, (HOUSEHOLD,))
    tz = ZoneInfo(timezone)
    # The scan runs before dawn; messages go out at the first hour delivery rules allow.
    send_at = clock(DeliveryRules.from_policy(policy).send_from_hour, 0)
    happened = {d["day"]: d["what_happened"] for d in backtest["timeline"]}
    mornings = []
    for outlook in morning_outlooks(backtest):
        meter.reset()
        pipeline = make_pipeline(lambda lat, lon, name, o=outlook: o, meter, ledger, outbox, policy)
        started = time.monotonic()
        rec = pipeline.run(group, datetime.combine(date.fromisoformat(outlook["issue_date"]), send_at, tz))
        mornings.append(ReplayMorning(
            day=outlook["issue_date"], code_flagged=rec.hazard_kind, what_happened=happened[outlook["issue_date"]],
            message=rec.final_text if rec.hazard_kind else None, draft=rec.draft,
            used_fallback=rec.used_fallback, model_error=rec.model_error, evaluator_sent_back=rec.evaluator_sent_back,
            delivered=rec.deliveries.get(HOUSEHOLD), seconds=round(time.monotonic() - started, 2),
            usage=meter.usage()))
    return AgentReplay(event["id"], backtest["place"], language, model_id, event.get("event_day"), mornings)
