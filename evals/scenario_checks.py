"""Deterministic scenario checks (plain functions, unit-tested), wrapped as strands-evals
Evaluators in run_scenarios.py. A scenario passes only if the live Evaluator rules also pass."""

import tomllib
from pathlib import Path

from weatherwise.agents.message_rules import MessageContext, MessageRules, check_message

SCENARIOS = Path(__file__).parent / "scenarios.toml"


def load_scenarios(path: Path = SCENARIOS) -> list[dict]:
    return tomllib.loads(path.read_text())["case"]


def check_reply(case: dict, reply: str, tools_called: list[str], rules: MessageRules,
                allowed_numbers: frozenset[float] = frozenset()) -> list[str]:
    """Problems with a reply for a scenario; empty list = pass."""
    problems = []
    low = reply.lower()
    for name in case.get("must_call", []):
        if name not in tools_called:
            problems.append(f"did not call {name}")
    for name in case.get("must_not_call", []):
        if name in tools_called:
            problems.append(f"called {name}")
    for text in case.get("must_contain", []):
        if text.lower() not in low:
            problems.append(f"missing {text!r}")
    for text in case.get("must_not_contain", []):
        if text.lower() in low:
            problems.append(f"contains {text!r}")
    ctx = MessageContext(hazards=(), allowed_numbers=allowed_numbers)
    for v in check_message(reply, ctx, rules):
        if v.rule != "unsupported_number" or allowed_numbers:
            problems.append(f"safety rule {v.rule}: {v.detail}")
    return problems
