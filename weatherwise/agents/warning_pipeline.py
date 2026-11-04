"""Scheduled warning pipeline (Strands Graph), one run per recipient group:

    risk_scan (code) --heat/dry--> warning_writer   (agent + Evaluator) --+--> final_gate (code) --> send (code)
               |--flood guide--> flood_writer     (agent + Evaluator) --|
               \\--all clear--> all_clear_writer (agent + Evaluator) --/

- risk_scan: hazard_outlook for the group's place, and what the agent told this place in the last
  few days (place memory: AgentCore Memory in production). Nothing found and nothing to clear ->
  the run stops (no AI cost). Nothing found after a recent warning -> the all-clear.
- writers: Strands agents with skills and Evaluator steering (rewrite up to 2 times).
- final_gate: the same code rules once more, then the safe fallback if anything is still wrong;
  adds the footer (plan §5.1).
- send: delivery rules per person (quiet hours, monthly cap, per-event limit) -> outbox (SQS in
  production) and the ledger. The message is saved to place memory for tomorrow's run.
Code nodes share one structured RunRecord instead of parsing each other's text.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from strands import Agent, AgentSkills
from strands.agent.agent_result import AgentResult
from strands.multiagent import GraphBuilder
from strands.multiagent.base import MultiAgentBase, MultiAgentResult, NodeResult, Status
from strands.telemetry.metrics import EventLoopMetrics

from weatherwise.agents.delivery import DeliveryLedger, DeliveryRules, Outbox, SentRecord, delivery_decision
from weatherwise.agents.message_rules import MessageRules, check_message
from weatherwise.agents.orchestrator import SKILLS, fallback_message
from weatherwise.agents.place_memory import PlaceMemory, open_warning, place_actor, recent
from weatherwise.agents.steering import SafetyRulesHandler, ToneHandler, context_from_tools
from weatherwise.risk.models import Hazard

HEAT_DRY = {Hazard.HEAT_WAVE.value, Hazard.WORK_HEAT.value, Hazard.EXCESS_HEAT.value,
            Hazard.DRY_SPELL.value, Hazard.SOWING_RISK.value}

WRITER_PROMPT = """You write ONE early-warning message for a group of people who share a place,
language, crop and water source. The facts are in the task as JSON from the risk scan: use only
those numbers. Follow the matching skill. Language: {language}. Do not add a footer (the system
adds it). Under 700 characters. Write only the words the person will read: no greeting, no tool or
skill names, no notes about what you are doing, nothing copied from these instructions.
Include every helpline number in the facts' helplines_to_include.
A flood or heavy-rain warning must also tell people, in {language}: {flood_lines}.
If the facts include earlier_warnings, people already have those messages: begin with what has
changed since the latest one (worse, the same or easing) and do not repeat it word for word."""


@dataclass(frozen=True)
class RecipientGroupRun:
    place_name: str
    lat: float
    lon: float
    language: str
    crop: str | None
    water_source: str | None
    subscriber_ids: tuple[str, ...]


@dataclass
class RunRecord:
    group: RecipientGroupRun
    now: datetime
    outlook: dict | None = None
    hazard_kind: str | None = None          # "heat_dry" | "flood" | "all_clear" | None
    earlier_warnings: list[dict] = field(default_factory=list)  # from place memory, last few days
    body: str | None = None                 # the message without the footer (what memory keeps)
    draft: str | None = None
    final_text: str | None = None
    used_fallback: bool = False
    violations: list[str] = field(default_factory=list)
    evaluator_sent_back: list[list[str]] = field(default_factory=list)  # each draft the Evaluator returned, and why
    deliveries: dict[str, str] = field(default_factory=dict)  # subscriber -> send/defer/skip
    rules_version_mismatch: bool = False  # the outlook and the policy came from different rule versions
    model_error: str | None = None  # the writer failed (e.g. hit its token limit): the safe message went out


def _text_result(text: str) -> AgentResult:
    return AgentResult(stop_reason="end_turn",
                       message={"role": "assistant", "content": [{"text": text}]},
                       metrics=EventLoopMetrics(), state={})


class CodeNode(MultiAgentBase):
    """A plain-code step in the Graph (no AI)."""

    def __init__(self, name: str, fn: Callable[[], str]):
        super().__init__()
        self.name, self.fn = name, fn

    async def invoke_async(self, task, invocation_state=None, **kwargs) -> MultiAgentResult:
        output = self.fn()
        return MultiAgentResult(status=Status.COMPLETED,
                                results={self.name: NodeResult(result=_text_result(output))})


def _event_key(outlook: dict) -> str:
    d = sorted(outlook["detections"], key=lambda x: x["first_day"])
    return f"{d[0]['hazard']}:{d[0]['first_day']}" if d else f"flood_guide:{outlook['issue_date']}"


class WarningPipeline:
    def __init__(self, outlook_fn: Callable[[float, float, str | None], dict], model, ledger: DeliveryLedger,
                 outbox: Outbox, policy: dict, with_tone_check: bool = True, tone_model=None,
                 memory: PlaceMemory | None = None):
        """policy: the MCP message_policy reply for the group's country. memory: what the agent
        told each place before; without it every morning starts fresh (no updates, no all-clear)."""
        self.memory = memory
        self.outlook_fn = outlook_fn
        self.policy = policy
        self.model = model
        self.ledger, self.outbox = ledger, outbox
        self.with_tone_check, self.tone_model = with_tone_check, tone_model

    def _writer(self, name: str, skills: list[str], rules: MessageRules, language: str) -> Agent:
        plugins = [AgentSkills(skills=[str(SKILLS / s) for s in skills]),
                   SafetyRulesHandler(rules, trust_input_data=True)]
        if self.with_tone_check:
            plugins.append(ToneHandler(model=self.tone_model))
        return Agent(name=name, model=self.model, system_prompt=WRITER_PROMPT.format(
                         language=language, flood_lines="; ".join(rules.flood_must_say)),
                     plugins=plugins, callback_handler=None)

    def run(self, group: RecipientGroupRun, now: datetime) -> RunRecord:
        rec = RunRecord(group, now)
        rules = MessageRules.from_policy(self.policy)
        delivery = DeliveryRules.from_policy(self.policy)
        warning_writer = self._writer("warning_writer", ["heat-advice", "drought-advice"], rules, group.language)
        flood_writer = self._writer(
            "flood_writer", ["flood-prepare-village", "flood-prepare-city", "flood-urgent"], rules, group.language)
        all_clear_writer = self._writer("all_clear_writer", ["all-clear"], rules, group.language)
        writers = {"heat_dry": warning_writer, "flood": flood_writer, "all_clear": all_clear_writer}
        actor = place_actor(group.lat, group.lon)

        def risk_scan() -> str:
            rec.outlook = self.outlook_fn(group.lat, group.lon, group.place_name)
            server_version = rec.outlook.get("rules_version")
            rec.rules_version_mismatch = server_version is not None and server_version != self.policy.get("rules_version")
            kinds = {d["hazard"] for d in rec.outlook["detections"]}
            if self.memory is not None:
                rec.earlier_warnings = recent(self.memory.recall(actor), now.date())
            if rec.outlook["flood_guide"]["mode"]:
                rec.hazard_kind = "flood"
            elif kinds & HEAT_DRY:
                rec.hazard_kind = "heat_dry"
            elif not kinds and open_warning(rec.earlier_warnings):
                rec.hazard_kind = "all_clear"
            facts = {"group": {"place": group.place_name, "crop": group.crop,
                               "water_source": group.water_source, "language": group.language},
                     **rec.outlook}
            # Code picks the helplines, so the message has exactly the ones the checker requires
            # (Nov 3 2026 eval: given every hazard's numbers, the model listed them all or dropped some).
            facts["helplines_to_include"] = sorted({n for h in context_from_tools([rec.outlook]).hazards
                                                    for n in rules.required_numbers.get(h, [])})
            if rec.earlier_warnings:
                facts["earlier_warnings"] = [{"day": e["day"], "kind": e["kind"], "message": e["message"]}
                                             for e in rec.earlier_warnings]
            return json.dumps(facts)

        def final_gate() -> str:
            writer = writers[rec.hazard_kind]
            rec.draft = next((b["text"] for m in reversed(writer.messages) if m["role"] == "assistant"
                              for b in m["content"] if "text" in b), "")
            ctx = context_from_tools([rec.outlook])
            problems = check_message(rec.draft, ctx, rules)
            rec.violations = [v.rule for v in problems]
            rec.evaluator_sent_back = writer.state.get("evaluator_log") or []
            rec.used_fallback = bool(problems) or bool(writer.state.get("use_fallback")) or rec.model_error is not None
            kind = ("flood" if rec.hazard_kind == "flood" else "all_clear" if rec.hazard_kind == "all_clear"
                    else "heat" if ctx.hazards and "heat" in ctx.hazards else "general")
            rec.body = fallback_message(self.policy, kind, group.language) if rec.used_fallback else rec.draft
            rec.final_text = f"{rec.body}\n\n{delivery.footer_for(group.language)}"
            return rec.final_text

        def send() -> str:
            urgent = rec.outlook["flood_guide"]["mode"] == "urgent"
            key = (f"all_clear:{open_warning(rec.earlier_warnings)['event_key']}" if rec.hazard_kind == "all_clear"
                   else _event_key(rec.outlook))
            for sid in group.subscriber_ids:
                decision = delivery_decision(sid, key, urgent, now, self.ledger, delivery)
                rec.deliveries[sid] = decision
                if decision == "send":
                    self.outbox.enqueue(sid, rec.final_text, {"event_key": key, "urgent": urgent})
                    self.ledger.add(SentRecord(sid, key, now, urgent))
            return json.dumps(rec.deliveries)

        b = GraphBuilder()
        b.add_node(CodeNode("risk_scan", risk_scan), "risk_scan")
        b.add_node(warning_writer, "warning_writer")
        b.add_node(flood_writer, "flood_writer")
        b.add_node(all_clear_writer, "all_clear_writer")
        b.add_node(CodeNode("final_gate", final_gate), "final_gate")
        b.add_node(CodeNode("send", send), "send")
        b.add_edge("risk_scan", "warning_writer", condition=lambda s: rec.hazard_kind == "heat_dry")
        b.add_edge("risk_scan", "flood_writer", condition=lambda s: rec.hazard_kind == "flood")
        b.add_edge("risk_scan", "all_clear_writer", condition=lambda s: rec.hazard_kind == "all_clear")
        b.add_edge("warning_writer", "final_gate")
        b.add_edge("flood_writer", "final_gate")
        b.add_edge("all_clear_writer", "final_gate")
        b.add_edge("final_gate", "send")
        b.set_entry_point("risk_scan")
        b.set_max_node_executions(10)
        graph = b.build()
        try:
            graph(f"Scheduled warning run for {group.place_name} on {now.date()}")
        except Exception as e:
            # A model failure must never mean no warning: code already decided to warn, so the
            # pre-written safe message goes out instead.
            if not rec.hazard_kind or rec.final_text is not None:
                raise
            rec.model_error = f"{type(e).__name__}: {e}"[:200]
            final_gate()
            send()
        if self.memory is not None and rec.hazard_kind and rec.body:
            self.memory.remember(actor, {
                "day": now.date().isoformat(), "kind": rec.hazard_kind,
                "event_key": open_warning(rec.earlier_warnings)["event_key"] if rec.hazard_kind == "all_clear"
                else _event_key(rec.outlook),
                "message": rec.body})
        return rec


def run_report(rec: RunRecord, outbox: Outbox, usage: dict, seconds: float) -> dict:
    """One morning's run as JSON: what code found, what the agent wrote, what the Evaluator sent
    back, what would be delivered, and what it cost in model calls and time."""
    o = rec.outlook or {}
    return {"hazard_kind": rec.hazard_kind, "used_fallback": rec.used_fallback,
            "rules_version_mismatch": rec.rules_version_mismatch, "violations": rec.violations,
            "deliveries": rec.deliveries, "outbox": getattr(outbox, "messages", []),
            "issue_date": o.get("issue_date"), "detections": o.get("detections", []),
            "flood_guide": o.get("flood_guide"), "data_missing": o.get("data_missing", []),
            "official": (o.get("official") or {}).get("alerts", []),
            "draft": rec.draft, "body": rec.body, "message": rec.final_text,
            "evaluator_sent_back": rec.evaluator_sent_back,
            "earlier_warnings": rec.earlier_warnings,
            "model_error": rec.model_error,
            "seconds": round(seconds, 2), **usage}
