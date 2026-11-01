"""Scheduled warning pipeline (Strands Graph), one run per recipient group:

    risk_scan (code) --heat/dry--> warning_writer (agent + Evaluator) --+--> final_gate (code) --> send (code)
               \\--flood guide--> flood_writer   (agent + Evaluator) --/

- risk_scan: hazard_outlook for the group's place. Nothing found -> the run stops (no AI cost).
- writers: Strands agents with skills and Evaluator steering (rewrite up to 2 times).
- final_gate: the same code rules once more, then the safe fallback if anything is still wrong;
  adds the footer (plan §5.1).
- send: delivery rules per person (quiet hours, monthly cap, per-event limit) -> outbox (SQS in
  production) and the ledger.
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
from weatherwise.agents.steering import SafetyRulesHandler, ToneHandler, context_from_tools
from weatherwise.risk.models import Hazard

HEAT_DRY = {Hazard.HEAT_WAVE.value, Hazard.WORK_HEAT.value, Hazard.EXCESS_HEAT.value,
            Hazard.DRY_SPELL.value, Hazard.SOWING_RISK.value}

WRITER_PROMPT = """You write ONE early-warning message for a group of people who share a place,
language, crop and water source. The facts are in the task as JSON from the risk scan: use only
those numbers. Follow the matching skill. Language: {language}. Do not add a footer (the system
adds it). Under 700 characters."""


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
    hazard_kind: str | None = None          # "heat_dry" | "flood" | None
    draft: str | None = None
    final_text: str | None = None
    used_fallback: bool = False
    violations: list[str] = field(default_factory=list)
    deliveries: dict[str, str] = field(default_factory=dict)  # subscriber -> send/defer/skip
    rules_version_mismatch: bool = False  # the outlook and the policy came from different rule versions


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
                 outbox: Outbox, policy: dict, with_tone_check: bool = True, tone_model=None):
        """policy: the MCP message_policy reply for the group's country."""
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
        return Agent(name=name, model=self.model, system_prompt=WRITER_PROMPT.format(language=language),
                     plugins=plugins, callback_handler=None)

    def run(self, group: RecipientGroupRun, now: datetime) -> RunRecord:
        rec = RunRecord(group, now)
        rules = MessageRules.from_policy(self.policy)
        delivery = DeliveryRules.from_policy(self.policy)
        warning_writer = self._writer("warning_writer", ["heat-advice", "drought-advice"], rules, group.language)
        flood_writer = self._writer(
            "flood_writer", ["flood-prepare-village", "flood-prepare-city", "flood-urgent"], rules, group.language)

        def risk_scan() -> str:
            rec.outlook = self.outlook_fn(group.lat, group.lon, group.place_name)
            server_version = rec.outlook.get("rules_version")
            rec.rules_version_mismatch = server_version is not None and server_version != self.policy.get("rules_version")
            kinds = {d["hazard"] for d in rec.outlook["detections"]}
            if rec.outlook["flood_guide"]["mode"]:
                rec.hazard_kind = "flood"
            elif kinds & HEAT_DRY:
                rec.hazard_kind = "heat_dry"
            facts = {"group": {"place": group.place_name, "crop": group.crop,
                               "water_source": group.water_source, "language": group.language},
                     **rec.outlook}
            return json.dumps(facts)

        def final_gate() -> str:
            writer = flood_writer if rec.hazard_kind == "flood" else warning_writer
            rec.draft = next((b["text"] for m in reversed(writer.messages) if m["role"] == "assistant"
                              for b in m["content"] if "text" in b), "")
            ctx = context_from_tools([rec.outlook])
            problems = check_message(rec.draft, ctx, rules)
            rec.violations = [v.rule for v in problems]
            rec.used_fallback = bool(problems) or bool(writer.state.get("use_fallback"))
            kind = "flood" if rec.hazard_kind == "flood" else "heat" if ctx.hazards and "heat" in ctx.hazards else "general"
            body = fallback_message(self.policy, kind, group.language) if rec.used_fallback else rec.draft
            rec.final_text = f"{body}\n\n{delivery.footer_for(group.language)}"
            return rec.final_text

        def send() -> str:
            urgent = rec.outlook["flood_guide"]["mode"] == "urgent"
            key = _event_key(rec.outlook)
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
        b.add_node(CodeNode("final_gate", final_gate), "final_gate")
        b.add_node(CodeNode("send", send), "send")
        b.add_edge("risk_scan", "warning_writer", condition=lambda s: rec.hazard_kind == "heat_dry")
        b.add_edge("risk_scan", "flood_writer", condition=lambda s: rec.hazard_kind == "flood")
        b.add_edge("warning_writer", "final_gate")
        b.add_edge("flood_writer", "final_gate")
        b.add_edge("final_gate", "send")
        b.set_entry_point("risk_scan")
        b.set_max_node_executions(10)
        graph = b.build()
        graph(f"Scheduled warning run for {group.place_name} on {now.date()}")
        return rec
