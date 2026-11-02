"""A scripted Strands model for tests and evals: plays back fixed replies and tool calls, no network.

Each item in the script is either a string (a final text reply), ("tool", name, input), or a
dict: the answer to a structured-output request (Strands asks for it as a call to the one tool
it offers). delay_seconds stands in for a real model's response time.
"""

import asyncio
import json
from collections.abc import AsyncIterable
from typing import Any

from strands.models import Model


class ScriptedModel(Model):
    def __init__(self, script: list, delay_seconds: float = 0.0):
        self.script = list(script)
        self.calls = 0
        self.delay_seconds = delay_seconds

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> Any:
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs) -> AsyncIterable[dict]:
        self.calls += 1
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        step = self.script.pop(0) if self.script else "(script finished)"
        if isinstance(step, dict):
            step = ("tool", tool_specs[-1]["name"], step)
        yield {"messageStart": {"role": "assistant"}}
        if isinstance(step, tuple) and step[0] == "tool":
            _, name, args = step
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{self.calls}", "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": step}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
