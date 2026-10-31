"""What the website can ask for, independent of the web framework (plan §9.2).

Every fact comes from the Climate Risk MCP server through `call`; chat goes to the same agent
team as WhatsApp. Chat sessions store nothing personal and never send WhatsApp messages.
"""

import time
import tomllib
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPLAYS_FILE = ROOT / "evals" / "headline_events.toml"
HAZARDS = {"heat", "flood", "cyclone", "other"}
LANGUAGES = {"en", "hi", "mr"}


class BadRequest(ValueError):
    """The page sent something we refuse; the message is safe to show."""


class NotCovered(ValueError):
    """The place is in a country WeatherWise has no rules for yet."""

    def __init__(self, answer: dict):
        super().__init__(f"not covered: {answer.get('country_code')}")
        self.country_code = answer.get("country_code", "")
        self.covered_countries = answer.get("covered_countries", [])


def _covered(answer: dict) -> dict:
    if answer.get("covered") is False:
        raise NotCovered(answer)
    return answer


class AgentsOffline(RuntimeError):
    """Chat needs Claude on Bedrock, which is not configured on this server."""


class DemoBusy(RuntimeError):
    """A rate limit or the daily chat cap was reached."""


@dataclass
class Limits:
    max_message_chars: int = 500
    chats_per_minute_per_visitor: int = 6
    chats_per_day: int = 500          # the daily AI-spend cap (plan §9.2 rule 3)
    max_sessions: int = 300           # oldest sessions are dropped beyond this
    session_seconds: int = 24 * 3600  # demo sessions expire after 24 h


def _number(value, name: str, low: float, high: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise BadRequest(f"{name} must be a number") from None
    if not low <= x <= high:
        raise BadRequest(f"{name} must be between {low} and {high}")
    return x


@dataclass
class WeatherWiseApi:
    call: Callable[[str, dict], dict]           # a Climate Risk MCP tool call
    team_factory: Callable[[dict, str], object] | None  # (policy, language) -> AgentTeam; None = offline
    limits: Limits = field(default_factory=Limits)
    clock: Callable[[], float] = time.time
    _sessions: OrderedDict = field(default_factory=OrderedDict)
    _visitor_chats: dict = field(default_factory=dict)
    _day: tuple = (None, 0)
    _replays: dict = field(default_factory=dict)
    _policies: dict = field(default_factory=dict)

    # ---- facts (no AI) ---------------------------------------------------------------
    def status(self) -> dict:
        return {"agents_ready": self.team_factory is not None, "languages": sorted(LANGUAGES),
                "limits": {"max_message_chars": self.limits.max_message_chars}}

    def policy(self, country: str = "in") -> dict:
        if country not in self._policies:
            self._policies[country] = self.call("message_policy", {"country_code": country})
        return self._policies[country]

    def find_place(self, query: str) -> dict:
        query = (query or "").strip()
        if not 2 <= len(query) <= 80:
            raise BadRequest("type 2 to 80 characters")
        return self.call("find_place", {"name": query})

    def place(self, lat, lon) -> dict:
        """What we know about the point, plus its outlook (the risk strip)."""
        lat, lon = _number(lat, "lat", -90, 90), _number(lon, "lon", -180, 180)
        place = _covered(self.call("resolve_place", {"lat": lat, "lon": lon}))
        return {"place": place, "outlook": _covered(self.call("hazard_outlook", {"lat": lat, "lon": lon}))}

    def official(self, lat, lon) -> dict:
        """Official warnings in force, asked separately from the forecast so they still show
        when the weather service is down."""
        lat, lon = _number(lat, "lat", -90, 90), _number(lon, "lon", -180, 180)
        return _covered(self.call("official_alerts", {"lat": lat, "lon": lon}))

    def shelters(self, lat, lon, hazard: str) -> dict:
        if hazard not in HAZARDS:
            raise BadRequest(f"hazard must be one of {sorted(HAZARDS)}")
        return _covered(self.call("find_shelters", {"lat": _number(lat, "lat", -90, 90),
                                                    "lon": _number(lon, "lon", -180, 180), "hazard": hazard}))

    def replays(self) -> list[dict]:
        events = tomllib.loads(REPLAYS_FILE.read_text())["replay"]
        return [{**{k: e[k] for k in ("id", "title", "name", "lat", "lon", "first_day", "last_day")},
                 "titles": {lang: e.get(f"title_{lang}", e["title"]) for lang in sorted(LANGUAGES)}}
                for e in events]

    def replay(self, replay_id: str) -> dict:
        """A real past event, replayed with only the forecasts that existed then."""
        if replay_id not in self._replays:
            event = next((e for e in self.replays() if e["id"] == replay_id), None)
            if event is None:
                raise BadRequest("unknown replay")
            result = self.call("backtest", {"lat": event["lat"], "lon": event["lon"],
                                            "first_day": event["first_day"], "last_day": event["last_day"],
                                            "place_name": event["name"]})
            self._replays[replay_id] = {"event": event, **result}
        return self._replays[replay_id]

    # ---- chat (the agents) -----------------------------------------------------------
    def _check_limits(self, visitor: str) -> None:
        now = self.clock()
        today = date.fromtimestamp(now)
        day, count = self._day
        if day != today:
            day, count = today, 0
        if count >= self.limits.chats_per_day:
            raise DemoBusy("The demo is busy today. Please watch the video instead.")
        recent = self._visitor_chats.setdefault(visitor, deque())
        while recent and now - recent[0] > 60:
            recent.popleft()
        if len(recent) >= self.limits.chats_per_minute_per_visitor:
            raise DemoBusy("Too many messages in a minute. Please wait a moment.")
        recent.append(now)
        self._day = (day, count + 1)

    def _team(self, session_id: str, language: str):
        now = self.clock()
        for sid in [s for s, (_, started) in self._sessions.items()
                    if now - started > self.limits.session_seconds]:
            del self._sessions[sid]
        key = f"{session_id}:{language}"
        if key not in self._sessions:
            if len(self._sessions) >= self.limits.max_sessions:
                self._sessions.popitem(last=False)
            self._sessions[key] = (self.team_factory(self.policy(), language), now)
        return self._sessions[key][0]

    def chat(self, visitor: str, session_id: str, message: str, language: str,
             place: dict | None = None) -> dict:
        if self.team_factory is None:
            raise AgentsOffline("The agents are not connected on this server yet. "
                                "Everything else on the page works without them.")
        if not session_id or not 33 <= len(session_id) <= 64:
            raise BadRequest("session_id must be a UUID")
        message = (message or "").strip()
        if not 1 <= len(message) <= self.limits.max_message_chars:
            raise BadRequest(f"message must be 1 to {self.limits.max_message_chars} characters")
        if language not in LANGUAGES:
            raise BadRequest(f"language must be one of {sorted(LANGUAGES)}")
        self._check_limits(visitor)
        if place:
            # The saved place comes from the system (the page's picker), never from the message.
            name = str(place.get("name", ""))[:80]
            lat, lon = _number(place.get("lat"), "lat", -90, 90), _number(place.get("lon"), "lon", -180, 180)
            message = (f"[System: the person's saved place is {name} (lat {lat}, lon {lon}); "
                       f"it is already confirmed.]\n{message}")
        started = self.clock()
        reply = self._team(session_id, language).reply(message)
        return {**reply, "seconds": round(self.clock() - started, 1)}
