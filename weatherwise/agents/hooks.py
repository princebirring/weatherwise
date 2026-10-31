"""Hooks (workshop Module 2): limits in code, not in prompts (plan §8.8.2)."""

import time

from strands.hooks import (
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)


class CostGuardHook(HookProvider):
    """Caps calls per tool and total tool calls per request, so a runaway loop cannot run up
    the Bedrock bill. Over the limit, the call is cancelled and the model is told why."""

    def __init__(self, max_calls_per_tool: int = 3, max_total_calls: int = 12):
        self.max_per_tool = max_calls_per_tool
        self.max_total = max_total_calls
        self.counts: dict[str, int] = {}

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.reset)
        registry.add_callback(BeforeToolCallEvent, self.check)

    def reset(self, event: BeforeInvocationEvent) -> None:
        self.counts = {}

    def check(self, event: BeforeToolCallEvent) -> None:
        name = event.tool_use["name"]
        self.counts[name] = self.counts.get(name, 0) + 1
        if self.counts[name] > self.max_per_tool:
            event.cancel_tool = f"'{name}' reached its limit of {self.max_per_tool} calls. Do not call it again."
        elif sum(self.counts.values()) > self.max_total:
            event.cancel_tool = "Tool-call limit for this request reached. Answer with what you have."


class StepLogHook(HookProvider):
    """Records each tool call (name, duration, ok/error) for the website's "how this answer was made"
    panel and CloudWatch. Tool inputs are not logged: they may contain a person's location."""

    def __init__(self):
        self.steps: list[dict] = []
        self._started: dict[str, float] = {}

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, lambda e: self.steps.clear())
        registry.add_callback(BeforeToolCallEvent, self.before)
        registry.add_callback(AfterToolCallEvent, self.after)

    def before(self, event: BeforeToolCallEvent) -> None:
        self._started[event.tool_use["toolUseId"]] = time.monotonic()

    def after(self, event: AfterToolCallEvent) -> None:
        started = self._started.pop(event.tool_use["toolUseId"], time.monotonic())
        status = (event.result or {}).get("status", "error" if event.exception else "success")
        self.steps.append({
            "agent": getattr(event.agent, "name", None) or "agent",
            "tool": event.tool_use["name"],
            "status": status,
            "seconds": round(time.monotonic() - started, 2),
        })
