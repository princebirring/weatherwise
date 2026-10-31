"""A scripted Strands model for tests: plays back fixed replies and tool calls, no network.

Each item in the script is either a string (a final text reply) or ("tool", name, input).
"""

import json
from collections.abc import AsyncIterable
from typing import Any

from strands.models import Model


class ScriptedModel(Model):
    def __init__(self, script: list):
        self.script = list(script)
        self.calls = 0

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> Any:
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs) -> AsyncIterable[dict]:
        self.calls += 1
        step = self.script.pop(0) if self.script else "(script finished)"
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
