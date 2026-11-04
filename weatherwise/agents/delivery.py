"""Delivery policy: quiet hours, monthly cap, per-event limit, footer.

The ledger and outbox are interfaces. Today both are in-memory: the morning run saves what each
place would receive to S3 (weatherwise/daily_run.py); sending to phones is not built yet.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class DeliveryRules:
    send_from_hour: int
    send_until_hour: int
    max_warnings_per_month: int
    max_messages_per_event: int
    footer: dict[str, str]

    @classmethod
    def from_policy(cls, policy: dict) -> "DeliveryRules":
        """Build from the MCP message_policy tool's reply."""
        d = policy["delivery"]
        return cls(d["send_from_hour"], d["send_until_hour"], d["max_warnings_per_month"],
                   d["max_messages_per_event"], policy["footer"])

    def footer_for(self, language: str) -> str:
        return self.footer.get(language) or self.footer["en"]


@dataclass(frozen=True)
class SentRecord:
    subscriber_id: str
    event_key: str
    sent_at: datetime
    urgent: bool


class DeliveryLedger(Protocol):
    def records_for(self, subscriber_id: str) -> list[SentRecord]: ...
    def add(self, record: SentRecord) -> None: ...


class Outbox(Protocol):
    def enqueue(self, subscriber_id: str, text: str, meta: dict) -> None: ...


@dataclass
class MemoryLedger:
    records: list[SentRecord] = field(default_factory=list)

    def records_for(self, subscriber_id: str) -> list[SentRecord]:
        return [r for r in self.records if r.subscriber_id == subscriber_id]

    def add(self, record: SentRecord) -> None:
        self.records.append(record)


@dataclass
class MemoryOutbox:
    messages: list[dict] = field(default_factory=list)

    def enqueue(self, subscriber_id: str, text: str, meta: dict) -> None:
        self.messages.append({"to": subscriber_id, "text": text, **meta})


def delivery_decision(subscriber_id: str, event_key: str, urgent: bool, now: datetime,
                      ledger: DeliveryLedger, rules: DeliveryRules) -> str:
    """"send", "defer" (quiet hours) or "skip" (a limit reached)."""
    if not urgent and not (rules.send_from_hour <= now.hour < rules.send_until_hour):
        return "defer"
    past = ledger.records_for(subscriber_id)
    if sum(1 for r in past if r.event_key == event_key) >= rules.max_messages_per_event:
        return "skip"
    if not urgent:
        this_month = [r for r in past if not r.urgent and (r.sent_at.year, r.sent_at.month) == (now.year, now.month)]
        if len(this_month) >= rules.max_warnings_per_month:
            return "skip"
    return "send"
