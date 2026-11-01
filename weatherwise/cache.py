"""Cache interface: files in development, DynamoDB/S3 in production (plan §8.9).

Entries are keyed by (kind, key), e.g. ("forecast", "cell:18.50:76.50"), and each kind
has its own time-to-live, so forecasts refresh within hours and baselines yearly.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Protocol

MINUTE = 60
HOUR = 3600
DAY = 24 * HOUR

TTL_SECONDS = {
    "forecast": 3 * HOUR,
    "recent": 3 * HOUR,
    "river_forecast": 3 * HOUR,
    "normals": 365 * DAY,
    "flood_level": 365 * DAY,
    "elevation": 3650 * DAY,
    "admin": 365 * DAY,
    "geocode": 30 * DAY,
    "health_facilities": 30 * DAY,
    "archive": 3650 * DAY,  # past data does not change
    "correction": DAY,      # each model's recent errors at a place: learned again every morning
    "official_alerts": 5 * MINUTE,       # official warnings change fast; ask again every 5 minutes
    "official_translation": 7 * DAY,     # a given alert's translation never changes
}


class Cache(Protocol):
    def get(self, kind: str, key: str) -> Any | None: ...
    def put(self, kind: str, key: str, value: Any) -> None: ...


class FileCache:
    """JSON files under root/<kind>/. Expired entries read as missing."""

    def __init__(self, root: str | Path, now=time.time):
        self.root = Path(root)
        self._now = now

    def _path(self, kind: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        return self.root / kind / f"{digest}.json"

    def get(self, kind: str, key: str) -> Any | None:
        path = self._path(kind, key)
        if not path.exists():
            return None
        entry = json.loads(path.read_text())
        if self._now() - entry["saved_at"] > TTL_SECONDS.get(kind, DAY):
            return None
        return entry["value"]

    def put(self, kind: str, key: str, value: Any) -> None:
        path = self._path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"key": key, "saved_at": self._now(), "value": value}))


class MemoryCache:
    """In-process cache for tests."""

    def __init__(self):
        self.entries: dict[tuple[str, str], Any] = {}

    def get(self, kind: str, key: str) -> Any | None:
        return self.entries.get((kind, key))

    def put(self, kind: str, key: str, value: Any) -> None:
        self.entries[(kind, key)] = value


def cached(cache: Cache, kind: str, key: str, compute):
    """Return the cached value, or compute, store and return it."""
    value = cache.get(kind, key)
    if value is None:
        value = compute()
        cache.put(kind, key, value)
    return value
