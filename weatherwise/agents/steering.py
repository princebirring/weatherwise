"""The Evaluator as Strands steering (workshop Module 3 pattern, plan §8.8.4).

SafetyRulesHandler (code): checks every final reply with check_message(); on a violation it
returns Guide, so the model rewrites. After MAX_REWRITES it lets the reply through but marks
agent.state "use_fallback", and the caller sends the region's safe pre-written message.

ToneHandler (AI): one more model call on the final reply judges calm tone, options-not-orders,
never contradicting official warnings, and plain local language. It runs after the reply is
written, not before each tool call (Strands' LLMSteeringHandler does the latter: an extra model
call per tool, judging tool calls against rules meant for replies).
"""

import json
from typing import Literal

from pydantic import BaseModel, Field
from strands import Agent
from strands.vended_plugins.steering import Guide, Proceed, SteeringHandler

from weatherwise.agents.message_rules import MessageContext, MessageRules, check_message, collect_numbers

MAX_REWRITES = 2
# The person reads the rewrite as-is, so no "Here's the revised response:" in front of it.
ONLY_THE_MESSAGE = "Write only the new message for the person; do not say that it was rewritten."


def _text(message: dict) -> str:
    return "".join(b.get("text", "") for b in message.get("content", []) if "text" in b)


def _tool_results(agent) -> list:
    """Every tool result in the conversation so far, parsed where possible."""
    results = []
    for msg in agent.messages:
        for block in msg.get("content", []):
            tr = block.get("toolResult")
            if not tr:
                continue
            for part in tr.get("content", []):
                if "json" in part:
                    results.append(part["json"])
                elif "text" in part:
                    try:
                        results.append(json.loads(part["text"]))
                    except (ValueError, TypeError):
                        results.append(part["text"])
    return results


def _system_input_data(agent) -> list:
    """JSON facts handed to the agent as its task by the pipeline (never used in chat, where
    the input is a person's message and could contain made-up numbers)."""
    found = []
    for msg in agent.messages:
        if msg.get("role") != "user":
            continue
        for block in msg.get("content", []):
            text = block.get("text", "")
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end > start:
                try:
                    found.append(json.loads(text[start:end + 1]))
                except ValueError:
                    pass
    return found


def context_from_tools(results: list) -> MessageContext:
    hazards: set[str] = set()
    urgent = False
    for r in results:
        if not isinstance(r, dict):
            continue
        for d in r.get("detections", []):
            h = d.get("hazard", "")
            if h in ("heat_wave", "work_heat", "excess_heat"):
                hazards.add("heat")
            elif h in ("heavy_rain", "unusual_rain"):
                hazards.add("heavy_rain")
            elif h == "river_flood":
                hazards.add("flood")
        mode = (r.get("flood_guide") or {}).get("mode")
        if mode:
            hazards.add("flood")
            urgent = urgent or mode == "urgent"
        if "place_type" in r:  # a find_shelters result
            hazards.add("shelter")
            if r.get("hazard") == "flood":
                hazards.add("flood")
            elif r.get("hazard") == "heat":
                hazards.add("heat")
    return MessageContext(tuple(sorted(hazards)), urgent, frozenset(collect_numbers(results)))


class SafetyRulesHandler(SteeringHandler):
    name = "evaluator-safety-rules"

    def __init__(self, rules: MessageRules, trust_input_data: bool = False):
        super().__init__()
        self.rules = rules
        self.trust_input_data = trust_input_data

    async def steer_after_model(self, *, agent, message, stop_reason, **kwargs):
        if stop_reason != "end_turn":
            return Proceed(reason="not a final reply")
        facts = _tool_results(agent) + (_system_input_data(agent) if self.trust_input_data else [])
        violations = check_message(_text(message), context_from_tools(facts), self.rules)
        if not violations:
            agent.state.set("evaluator_rewrites", 0)
            return Proceed(reason="all safety rules pass")
        rewrites = (agent.state.get("evaluator_rewrites") or 0) + 1
        agent.state.set("evaluator_rewrites", rewrites)
        agent.state.set("evaluator_violations", [v.rule for v in violations])
        if rewrites > MAX_REWRITES:
            agent.state.set("use_fallback", True)
            return Proceed(reason="rewrite limit reached; caller sends the safe fallback message")
        return Guide(reason="Rewrite the reply. Fix: " + "; ".join(f"{v.rule}: {v.detail}" for v in violations)
                     + ". " + ONLY_THE_MESSAGE)


TONE_POLICY = """You review a reply to a farmer or household before it is sent. Check that it:
- is calm and never alarming (some readers are in distress); no blame;
- gives options, not orders ("you could", "if you have well water");
- never contradicts or downplays an official IMD/government warning;
- uses simple, natural words in the person's language; no jargon, no English words a village
  reader would not know (except numbers and helplines);
- is short and answers what was asked.
If any rule is broken, say exactly what to change. Otherwise approve."""


MAX_TONE_REWRITES = 1


class ToneVerdict(BaseModel):
    decision: Literal["approve", "rewrite"] = Field(description="approve, or rewrite if any rule is broken")
    reason: str = Field(description="If rewrite: exactly what to change")


class ToneHandler(SteeringHandler):
    name = "evaluator-tone"

    def __init__(self, model=None):
        super().__init__()
        self.model = model

    async def steer_after_model(self, *, agent, message, stop_reason, **kwargs):
        if stop_reason != "end_turn":
            return Proceed(reason="not a final reply")
        rewrites = agent.state.get("tone_rewrites") or 0
        if rewrites >= MAX_TONE_REWRITES:
            agent.state.set("tone_rewrites", 0)
            return Proceed(reason="tone rewrite limit reached; the safety rules still apply")
        judge = Agent(system_prompt=TONE_POLICY, model=self.model or agent.model, callback_handler=None)
        verdict = (await judge.invoke_async(f"The reply:\n{_text(message)}",
                                            structured_output_model=ToneVerdict)).structured_output
        if verdict.decision == "approve":
            agent.state.set("tone_rewrites", 0)
            return Proceed(reason="tone approved")
        agent.state.set("tone_rewrites", rewrites + 1)
        return Guide(reason="Rewrite the reply for tone: " + verdict.reason + ". " + ONLY_THE_MESSAGE)
