"""Counts every model call and its tokens, so a run can report what it cost.

Wraps any Strands model. The writers and the tone check share one meter, because the tone
check uses the writer's model unless it is given its own.
"""

import time
import tomllib
from collections.abc import AsyncIterable
from functools import cache
from pathlib import Path
from typing import Any

from strands.models import Model

PRICES_FILE = Path(__file__).resolve().parents[2] / "data" / "bedrock_prices.toml"


@cache
def _prices() -> dict:
    return tomllib.loads(PRICES_FILE.read_text())


def cost_usd(input_tokens: int, output_tokens: int, model_id: str) -> float | None:
    """Model cost from the AWS list prices in data/bedrock_prices.toml; None for an unlisted model."""
    price = _prices().get(model_id)
    if not price:
        return None
    return round(input_tokens / 1000 * price["input"] + output_tokens / 1000 * price["output"], 5)


class MeteredModel(Model):
    def __init__(self, inner: Model):
        self.inner = inner
        self.reset()

    def reset(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.model_seconds = 0.0

    def usage(self) -> dict:
        return {"model_calls": self.calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "model_seconds": round(self.model_seconds, 2)}

    def update_config(self, **model_config: Any) -> None:
        self.inner.update_config(**model_config)

    def get_config(self) -> Any:
        return self.inner.get_config()

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        async for event in self.inner.structured_output(output_model, prompt, system_prompt=system_prompt, **kwargs):
            yield event

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs) -> AsyncIterable[dict]:
        self.calls += 1
        started = time.monotonic()
        try:
            async for event in self.inner.stream(messages, tool_specs, system_prompt, **kwargs):
                usage = event.get("metadata", {}).get("usage") if isinstance(event, dict) else None
                if usage:
                    self.input_tokens += usage.get("inputTokens", 0)
                    self.output_tokens += usage.get("outputTokens", 0)
                yield event
        finally:
            self.model_seconds += time.monotonic() - started
