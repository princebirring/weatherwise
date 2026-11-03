"""Cache interface: files in development; in production, files backed by a shared S3 bucket.

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
    """JSON files under root/<kind>/. Expired entries read as missing. read_only: a seed shipped
    with the app (places worked out before deploy), never written to."""

    def __init__(self, root: str | Path, now=time.time, read_only: bool = False):
        self.root = Path(root)
        self._now = now
        self.read_only = read_only

    def _path(self, kind: str, key: str) -> Path:
        return self.root / kind / f"{_digest(key)}.json"

    def get_entry(self, kind: str, key: str) -> dict | None:
        path = self._path(kind, key)
        return json.loads(path.read_text()) if path.exists() else None

    def put_entry(self, kind: str, key: str, entry: dict) -> None:
        if self.read_only:
            return
        path = self._path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(entry))

    def get(self, kind: str, key: str) -> Any | None:
        entry = self.get_entry(kind, key)
        return entry["value"] if entry and _fresh(entry, kind, self._now()) else None

    def put(self, kind: str, key: str, value: Any) -> None:
        self.put_entry(kind, key, {"key": key, "saved_at": self._now(), "value": value})


class S3Cache:
    """The same entries in an S3 bucket: shared by the website's container and the agents on
    AgentCore, and kept across deploys. A slow or missing bucket reads as a miss, never an error."""

    def __init__(self, bucket: str, prefix: str = "cache/", client=None):
        self.bucket = bucket
        self.prefix = prefix
        self.read_only = False
        if client is None:
            from boto3 import client as boto_client
            from botocore.config import Config

            client = boto_client("s3", config=Config(connect_timeout=2, read_timeout=5,
                                                     retries={"total_max_attempts": 2}))
        self.client = client

    def _key(self, kind: str, key: str) -> str:
        return f"{self.prefix}{kind}/{_digest(key)}.json"

    def get_entry(self, kind: str, key: str) -> dict | None:
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=self._key(kind, key))["Body"]
            return json.loads(body.read())
        except Exception:
            return None

    def put_entry(self, kind: str, key: str, entry: dict) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=self._key(kind, key),
                                   Body=json.dumps(entry).encode(), ContentType="application/json")
        except Exception:
            pass


class LayeredCache:
    """Nearest layer first (this container's disk, then the shared bucket, then the shipped seed).
    A hit in a further layer is copied into the nearer ones with its original saved_at, so its
    time-to-live never restarts."""

    def __init__(self, layers: list, now=time.time):
        self.layers = layers
        self._now = now

    def get(self, kind: str, key: str) -> Any | None:
        for i, layer in enumerate(self.layers):
            entry = layer.get_entry(kind, key)
            if entry and _fresh(entry, kind, self._now()):
                for nearer in self.layers[:i]:
                    nearer.put_entry(kind, key, entry)
                return entry["value"]
        return None

    def put(self, kind: str, key: str, value: Any) -> None:
        entry = {"key": key, "saved_at": self._now(), "value": value}
        for layer in self.layers:
            layer.put_entry(kind, key, entry)


def _digest(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def _fresh(entry: dict, kind: str, now: float) -> bool:
    return now - entry["saved_at"] <= TTL_SECONDS.get(kind, DAY)


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
