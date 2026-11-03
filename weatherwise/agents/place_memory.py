"""What the morning agent told each place before: AgentCore Memory (short-term events).

One actor per place, one session for its morning warnings. Each warning or all-clear the
warning Graph writes is saved as one event; the next morning the Graph reads the recent ones, so
the agent writes an update ("since yesterday the river has risen") instead of repeating itself,
and says when a warning is over. Only what the agent wrote is kept: nothing about people.

    AgentCorePlaceMemory   production (WEATHERWISE_MEMORY_ID, created by the CloudFormation stack)
    LocalPlaceMemory       development and tests (in memory, or a JSON file across runs)
"""

import json
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

SESSION = "morning-warnings"
LOOK_BACK_DAYS = 3   # an earlier warning older than this is no longer "the same event"


def place_actor(lat: float, lon: float) -> str:
    """A stable id for a place, from its coordinates (AgentCore actor ids allow no dots)."""
    ns, ew = "N" if lat >= 0 else "S", "E" if lon >= 0 else "W"
    return f"place-{abs(lat):05.2f}{ns}-{abs(lon):06.2f}{ew}".replace(".", "")


class PlaceMemory(Protocol):
    def recall(self, actor: str) -> list[dict]:
        """Every saved entry for this place, oldest first."""

    def remember(self, actor: str, entry: dict) -> None:
        """Save one entry: {"day", "kind", "hazards", "event_key", "message"}."""


def recent(entries: list[dict], today: date, days: int = LOOK_BACK_DAYS) -> list[dict]:
    """The entries from the last `days` days before today, oldest first."""
    since = today - timedelta(days=days)
    return [e for e in entries if since <= date.fromisoformat(e["day"]) < today]


def open_warning(entries: list[dict]) -> dict | None:
    """The latest warning not yet followed by an all-clear, if any."""
    latest = entries[-1] if entries else None
    return latest if latest and latest["kind"] != "all_clear" else None


class LocalPlaceMemory:
    def __init__(self, path: Path | None = None):
        self.path, self._lock = path, threading.Lock()  # the daily run writes from several threads
        self.entries: dict[str, list[dict]] = (
            json.loads(path.read_text()) if path is not None and path.is_file() else {})

    def recall(self, actor: str) -> list[dict]:
        return list(self.entries.get(actor, []))

    def remember(self, actor: str, entry: dict) -> None:
        with self._lock:
            self.entries.setdefault(actor, []).append(entry)
            if self.path is not None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.entries, ensure_ascii=False, indent=1))


class AgentCorePlaceMemory:
    def __init__(self, memory_id: str, region: str | None = None, client=None):
        if client is None:
            from bedrock_agentcore.memory import MemoryClient

            client = MemoryClient(region_name=region)
        self.client, self.memory_id = client, memory_id

    def recall(self, actor: str) -> list[dict]:
        events = self.client.list_events(memory_id=self.memory_id, actor_id=actor, session_id=SESSION,
                                         max_results=20)
        out = []
        for event in events:
            for item in event.get("payload", []):
                text = item.get("conversational", {}).get("content", {}).get("text")
                if text:
                    out.append(json.loads(text))
        return sorted(out, key=lambda e: e["day"])

    def remember(self, actor: str, entry: dict) -> None:
        self.client.create_event(memory_id=self.memory_id, actor_id=actor, session_id=SESSION,
                                 messages=[(json.dumps(entry, ensure_ascii=False), "ASSISTANT")])
