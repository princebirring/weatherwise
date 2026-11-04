"""Deterministic message rules: anything that could hurt someone is checked by code.

check_message() is a pure function, so every rule is unit-tested and can also run as the
final gate in the scheduled pipeline, outside any agent.
"""

import re
from dataclasses import dataclass, field

UNITS = ["°\\s*c", "°", "deg", "mm", "km", "%", "m3/s"]  # regex; per-language unit words come from rules/


@dataclass(frozen=True)
class MessageContext:
    hazards: tuple[str, ...]            # e.g. ("heat",), ("flood", "heavy_rain"), ("shelter",)
    urgent: bool = False
    allowed_numbers: frozenset[float] = frozenset()  # every number the tools returned
    official_alert: str | None = None


@dataclass(frozen=True)
class Violation:
    rule: str
    detail: str


@dataclass
class MessageRules:
    max_chars_reply: int
    max_chars_urgent: int
    required_numbers: dict[str, list[str]]
    banned_alone: list[str]
    unless_with: list[str]
    banned_in_flood: list[str]
    banned_always: list[str] = field(default_factory=list)
    claims_safe: list[str] = field(default_factory=list)
    unit_words: list[str] = field(default_factory=list)
    flood_must_say: dict[str, list[str]] = field(default_factory=dict)  # each line: any one of its words

    def __post_init__(self):
        words = sorted((re.escape(w) for w in self.unit_words), key=len, reverse=True)
        self.number = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(" + "|".join(words + UNITS) + ")", re.IGNORECASE)

    @classmethod
    def from_policy(cls, policy: dict) -> "MessageRules":
        """Build from the MCP message_policy tool's reply (the agent never reads rule files)."""
        m = policy["messages"]
        return cls(
            max_chars_reply=m["max_chars_reply"],
            max_chars_urgent=m["max_chars_urgent"],
            required_numbers=m["required_numbers"],
            banned_alone=m["high_ground_phrases"],
            unless_with=m["slope_safety_words"],
            banned_in_flood=m["no_links_in_floods"],
            banned_always=m["never_say"],
            claims_safe=m.get("claims_safe", []),
            unit_words=m.get("unit_words", []),
            flood_must_say=m.get("flood_must_say", {}),
        )


# "It is not safe to work" and "unsafe to work" are the right answer, not a claim of safety
# (Nov 3 2026: live chat blocked "not safe to work" until the request timed out).
NEGATION = re.compile(r"(\bnot|\bnever|n't|\bno longer)\s+$|\w$")


def claims(phrase: str, low: str) -> bool:
    """True if the text says the phrase itself, not its negation."""
    return any(not NEGATION.search(low[max(0, m.start() - 12):m.start()])
               for m in re.finditer(re.escape(phrase), low))


def numbers_in(text: str, rules: "MessageRules | None" = None) -> list[float]:
    """Numbers that carry a weather or distance unit (deg C, mm, km, %, m3/s, or a unit word
    such as "अंश" or "प्रतिशत" from the language files)."""
    pattern = (rules or _DEFAULT).number
    return [float(m.group(1)) for m in pattern.finditer(text)]


def _close_to_allowed(n: float, allowed: frozenset[float]) -> bool:
    return any(abs(n - a) <= max(0.51, abs(a) * 0.01) for a in allowed)  # rounding allowed


# Our own words that must never reach a person: tool and skill names (snake_case), the model's
# notes to itself, markup. Found in Nova Pro's Marathi replay drafts ("find_shelters हा आदेश वापरा").
INTERNAL_TEXT = re.compile(r"<\s*/?\s*[a-z_]+\s*>|\b[a-z]+_[a-z_]+\b|\bskills?\b", re.IGNORECASE)


def check_message(text: str, ctx: MessageContext, rules: MessageRules) -> list[Violation]:
    low = text.lower()
    found: list[Violation] = []

    leaked = INTERNAL_TEXT.search(text)
    if leaked:
        found.append(Violation("internal_text", f"remove {leaked.group(0)!r}: write only what the person reads"))

    limit = rules.max_chars_urgent if ctx.urgent else rules.max_chars_reply
    if len(text) > limit:
        found.append(Violation("too_long", f"{len(text)} characters; limit {limit}"))

    for hazard in ctx.hazards:
        for number in rules.required_numbers.get(hazard, []):
            if number not in text:
                found.append(Violation("missing_helpline", f"{hazard} message must include {number}"))

    if any(p.lower() in low for p in rules.banned_alone) and not any(
        w.lower() in low for w in rules.unless_with
    ):
        found.append(Violation("unsafe_high_ground",
                               "'high ground' needs 'away from hill slopes' in the same message"))

    if "flood" in ctx.hazards:
        for line, words in rules.flood_must_say.items():
            if not any(w.lower() in low for w in words):
                found.append(Violation("missing_flood_safety", f"a flood warning must say: {line}"))

    if {"flood", "heavy_rain"} & set(ctx.hazards):
        for p in rules.banned_in_flood:
            if p.lower() in low:
                found.append(Violation("map_route_in_flood", f"no links or routes in floods ({p!r})"))
                break

    for p in rules.banned_always:
        if p.lower() in low:
            found.append(Violation("banned_phrase", repr(p)))

    for p in rules.claims_safe:
        if claims(p.lower(), low):
            found.append(Violation("claims_safe", f"never tell someone they are safe ({p!r}); "
                                                  "give the facts and what they could do"))

    for n in numbers_in(text, rules):
        if not _close_to_allowed(n, ctx.allowed_numbers):
            found.append(Violation("unsupported_number",
                                   f"{n:g} does not come from the tool data"))
    return found


_DEFAULT = MessageRules(0, 0, {}, [], [], [])


def collect_numbers(value) -> set[float]:
    """Every number inside tool results (nested dicts/lists/JSON text), for allowed_numbers."""
    out: set[float] = set()
    if isinstance(value, bool):
        return out
    if isinstance(value, (int, float)):
        out.add(float(value))
        if 0 < value <= 1:
            out.add(round(float(value) * 100))  # agreement 0.83 may be written as 83%
    elif isinstance(value, str):
        out.update(float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", value))
    elif isinstance(value, dict):
        for v in value.values():
            out |= collect_numbers(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            out |= collect_numbers(v)
    return out
