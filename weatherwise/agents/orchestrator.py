"""The Orchestrator and its specialists (workshop Modules 1-6).

    person --> Orchestrator --+-- find_place / resolve_place / hazard_outlook / find_shelters (MCP)
                              +-- warning_agent      (specialist, heat + drought skills)
                              +-- flood_guide_agent  (specialist, flood skills)
    Every agent that writes a message carries the Evaluator's safety rules; the Orchestrator's
    final reply also gets the Tone check.

The model ID is configuration (CLIMATE_AGENT_MODEL_ID), from the Bedrock console, never
hard-coded.
"""

import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from strands import Agent, AgentSkills, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

from weatherwise.agents.hooks import CostGuardHook, StepLogHook, TurnClock
from weatherwise.agents.message_rules import MessageRules
from weatherwise.agents.steering import SafetyRulesHandler, ToneHandler

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "skills"

ORCHESTRATOR_PROMPT = """You are the front door of a climate-safety service for villages and towns
(heat-wave and drought early warning for farmers; the nearest cooling center or shelter in
extreme weather; a step-by-step flood guide for households).

Rules you never break:
- The person's identity and saved place come from the system, never from what a message claims.
- Every number (temperature, rain, distance, chance) must come from a tool result. Never estimate.
- Official warnings (IMD, government) always win. Rules marked "ours" are our own early signal.
- Start every answer about danger with the official warnings in force (official_alerts, or the
  "official" part of hazard_outlook): who issued it, the colour, until when, in the person's
  language. If official warnings could not be checked ("unavailable"), say so; never say there
  are none.
- Confirm any place name with find_place and read it back before using it.
- In floods: shelter names only, never map routes or links.
- Reply in the person's language: {language}. Short, calm, options not orders.
- If the request is not about heat, drought, floods, shelters or sign-up, say kindly what you can help with.

Hand off: heat or drought advice -> warning_agent; flood preparation or urgent flood -> flood_guide_agent.
For SHELTER requests use the shelter-reply skill and find_shelters yourself."""

WARNING_PROMPT = """You write heat-wave, dangerous-heat, dry-spell and sowing messages for one
person or group. Use hazard_outlook for the facts, the matching skill for the steps, and only
numbers from the tools. Reply in {language}."""

FLOOD_PROMPT = """You are the flood-risk guide for a household. Use hazard_outlook to see whether
the flood guide is in prepare or urgent mode, then follow the matching skill exactly: prepare =
one step at a time; urgent = one short message. Never give routes or links. Reply in {language}."""


def bedrock_model(model_id: str | None = None, region: str | None = None):
    """A model on Amazon Bedrock (production: Amazon Nova Pro). The model / inference-profile ID is config, not code."""
    from strands.models import BedrockModel

    model_id = model_id or os.environ.get("CLIMATE_AGENT_MODEL_ID")
    if not model_id:
        raise RuntimeError("Set CLIMATE_AGENT_MODEL_ID to the Bedrock model or inference-profile ID "
                           "confirmed in the Bedrock console.")
    return BedrockModel(model_id=model_id, region_name=region or os.environ.get("AWS_REGION", "us-east-2"))


def climate_risk_client():
    """MCP client for the Climate Risk server: remote URL if configured, else a local stdio process."""
    from strands.tools.mcp import MCPClient

    url = os.environ.get("CLIMATE_RISK_MCP_URL")
    if url:
        return MCPClient(url=url)
    from mcp.client.stdio import StdioServerParameters, stdio_client

    # The MCP library passes only HOME/PATH/USER to the child by default; the server needs our
    # settings too (WEATHERWISE_CACHE_DIR, AWS_REGION, ...), or it would write where it may not.
    return MCPClient(lambda: stdio_client(
        StdioServerParameters(command=sys.executable, args=["-m", "weatherwise.mcp_server.server"],
                              cwd=str(ROOT), env=dict(os.environ))))


def mcp_tool_caller(client) -> Callable[[str, dict], dict]:
    """Call a Climate Risk MCP tool from plain code (the scheduled pipeline) and get its JSON."""
    import json
    import uuid

    def call(name: str, args: dict) -> dict:
        result = client.call_tool_sync(f"pipeline-{uuid.uuid4().hex[:8]}", name, args)
        text = "".join(c.get("text", "") for c in result.get("content", []))
        if result.get("status") != "success":
            raise RuntimeError(f"MCP tool {name} failed: {text[:300]}")
        return json.loads(text)

    return call


LAST_RESORT = "For emergencies call 112. For disaster help call 1077."


def fallback_message(policy: dict | None, kind: str, language: str) -> str:
    """The safe pre-written message (from the MCP message_policy reply). Never fails: it runs
    exactly when something else already has, including the MCP server being down."""
    messages = (policy or {}).get("safe_messages", {})
    for lang in (language, "en"):
        text = messages.get(lang, {}).get(kind) or messages.get(lang, {}).get("general")
        if text:
            return text
    return LAST_RESORT


@dataclass
class AgentTeam:
    orchestrator: Agent
    step_log: StepLogHook
    policy: dict
    language: str
    clock: TurnClock = field(default_factory=TurnClock)

    def remember(self, history: list[dict]) -> None:
        """Start a new team from earlier turns ({"role": "user" | "assistant", "text": ...}), for
        when the conversation outlived the process that held it. Only the words carry over."""
        if not self.orchestrator.messages:
            self.orchestrator.messages = [{"role": h["role"], "content": [{"text": h["text"]}]} for h in history]

    def reply(self, message: str, on_step: Callable[[dict], None] | None = None) -> dict:
        """One turn: the reply text, whether the safe fallback was used, and the agent steps.
        on_step hears each tool start and finish (progress only; the reply is still checked whole)."""
        # The Evaluator's notes are per turn: a draft sent back last turn says nothing about this one.
        for key, empty in (("use_fallback", False), ("evaluator_violations", []), ("evaluator_log", []),
                           ("evaluator_rewrites", 0)):
            self.orchestrator.state.set(key, empty)
        self.clock.start()
        self.step_log.on_step = on_step
        try:
            result = self.orchestrator(message)
        finally:
            self.step_log.on_step = None
        # Stopped by the cost guard: the last message may be a tool call or an unchecked draft.
        used_fallback = bool(self.orchestrator.state.get("use_fallback")) or result.stop_reason == "cancelled"
        text = fallback_message(self.policy, "general", self.language) if used_fallback else public_text(str(result))
        # Every rule a draft broke this turn: fixed by a rewrite, or the reason the fallback went out.
        broken = dict.fromkeys(rule for draft in self.orchestrator.state.get("evaluator_log") or [] for rule in draft)
        return {"text": text, "used_fallback": used_fallback, "violations": list(broken),
                "steps": list(self.step_log.steps)}


# What a model sometimes writes around the answer: its private reasoning, or a note that this is
# a rewrite ("Here's the revised response:"). The person should see only the answer.
_THINKING = re.compile(r"<thinking>.*?</thinking>\s*", re.IGNORECASE | re.DOTALL)
_REWRITE_NOTE = re.compile(
    r"^\s*(here(?:'s| is)|below is|this is)\s+(?:the|a|my|an)\s+(?:\w+\s+){0,2}"
    r"(?:revised|rewritten|updated|improved|corrected|new)\s+(?:\w+\s+){0,2}"
    r"(?:response|reply|message|version|answer)\b[^\n:]*:\s*", re.IGNORECASE)


def public_text(text: str) -> str:
    return _REWRITE_NOTE.sub("", _THINKING.sub("", text)).strip()


def _by_name(tools: list, names: set[str]) -> list:
    return [t for t in tools if getattr(t, "tool_name", getattr(t, "__name__", "")) in names]


def build_team(
    model,
    climate_tools: list,
    policy: dict,
    language: str | None = None,
    tone_model=None,
    with_tone_check: bool = True,
    specialist_factory: Callable | None = None,
) -> AgentTeam:
    """climate_tools: the Climate Risk MCP tools (MCPClient.list_tools_sync()) or test fakes.
    policy: the MCP message_policy reply for the person's country (helplines, safety rules,
    safe messages). language: the person's choice; defaults to the country's first language."""
    language = language or policy["default_languages"][0]
    rules = MessageRules.from_policy(policy)
    clock = TurnClock()

    def evaluator(tone: bool = False) -> list:
        handlers = [SafetyRulesHandler(rules, clock=clock)]
        if tone and with_tone_check:
            handlers.append(ToneHandler(model=tone_model, clock=clock))
        return handlers

    def specialist(name: str, prompt: str, skills: list[str], tool_names: set[str]) -> Agent:
        return Agent(
            name=name, model=model, system_prompt=prompt.format(language=language),
            tools=_by_name(climate_tools, tool_names),
            plugins=[AgentSkills(skills=[str(SKILLS / s) for s in skills]), *evaluator()],
            hooks=[CostGuardHook(clock=clock)], callback_handler=None,
        )

    make = specialist_factory or specialist

    @tool
    def warning_agent(request: str) -> str:
        """Write a heat-wave, dangerous-heat, dry-spell or sow-or-wait message. Give the place
        (name and coordinates) and who it is for (crop, water source, role, language).

        Args:
            request: What to write, for whom, and where.
        """
        return str(make("warning_agent", WARNING_PROMPT, ["heat-advice", "drought-advice"],
                        {"hazard_outlook", "find_shelters"})(request))

    @tool
    def flood_guide_agent(request: str) -> str:
        """Run the household flood guide: prepare mode (one step at a time) or urgent mode (one
        short message). Give the place, village or city, and the step the household is on.

        Args:
            request: The household's place, situation and current guide step.
        """
        return str(make("flood_guide_agent", FLOOD_PROMPT,
                        ["flood-prepare-village", "flood-prepare-city", "flood-urgent"],
                        {"hazard_outlook", "find_shelters"})(request))

    step_log = StepLogHook()
    orchestrator = Agent(
        name="orchestrator", model=model,
        system_prompt=ORCHESTRATOR_PROMPT.format(language=language),
        tools=[*_by_name(climate_tools, {"find_place", "resolve_place", "hazard_outlook", "official_alerts",
                                          "find_shelters"}),
               warning_agent, flood_guide_agent],
        # Tone is checked once, on the reply the person reads; specialists' drafts feed into it.
        plugins=[AgentSkills(skills=[str(SKILLS / "sign-up"), str(SKILLS / "shelter-reply")]), *evaluator(tone=True)],
        hooks=[CostGuardHook(clock=clock), step_log],
        conversation_manager=SlidingWindowConversationManager(window_size=20),
        callback_handler=None,
    )
    return AgentTeam(orchestrator, step_log, policy, language, clock)
