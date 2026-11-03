"""What the website can ask for, independent of the web framework (plan §9.2).

Every fact comes from the Climate Risk MCP server through `call`; chat goes to the same agent
team as WhatsApp. Chat sessions store nothing personal and never send WhatsApp messages.
"""

import json
import re
import time
import tomllib
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from weatherwise.rules import country_for, load_rules, rules_version

ROOT = Path(__file__).resolve().parents[2]
REPLAYS_FILE = ROOT / "evals" / "headline_events.toml"
AGENT_REPLAYS_DIR = ROOT / "evals" / "results" / "agent_replays"
DAILY_SECONDS = 300  # how long a read of the morning run is reused
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
    chats_per_day: int = 100          # the daily AI-spend cap (plan §9.2 rule 3)
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
    daily_store: Callable[[str], dict | list | None] | None = None  # "latest" / "index" -> the morning run
    _daily: tuple = (0.0, None)

    # ---- facts (no AI) ---------------------------------------------------------------
    def status(self) -> dict:
        return {"agents_ready": self.team_factory is not None, "languages": sorted(LANGUAGES),
                "limits": {"max_message_chars": self.limits.max_message_chars}}

    def policy(self, country: str = "in") -> dict:
        if country not in self._policies:
            self._policies[country] = self.call("message_policy", {"country_code": country})
        return self._policies[country]

    def find_place(self, query: str, language: str | None = None) -> dict:
        query = (query or "").strip()
        if not 2 <= len(query) <= 80:
            raise BadRequest("type 2 to 80 characters")
        args = {"name": query}
        if language and language != "en":
            if language not in LANGUAGES:
                raise BadRequest("unknown language")
            args["language"] = language
        return self.call("find_place", args)

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

    def rules(self, country: str = "in") -> dict:
        """The lines our checks use, read from rules/ (never copied into the website), for the
        "how a warning is decided" diagram. Official lines and our own are kept apart."""
        r = load_rules(country_for(country))
        heat, rain, guide = r["heat"], r["heavy_rain"], r["flood_guide"]
        return {
            "country": country,
            "heat": {"base_tmax_c": heat["base_tmax"], "departure_c": heat["heat_wave_departure"],
                     "absolute_c": heat["heat_wave_absolute"], "min_days": heat["min_consecutive_days"],
                     "agreement": heat["min_agreement"],
                     "work_heat_c": {lv["name"]: lv["feels_like_c"] for lv in r["work_heat"]["levels"]},
                     "excess_heat_percentile": r["excess_heat"]["heat_percentile"]},
            "rain_mm": {k: rain[k] for k in ("heavy", "very_heavy", "extremely_heavy")},
            "unusual_rain": {"percentile": r["unusual_rain"]["percentile"], "min_mm": r["unusual_rain"]["min_mm"]},
            "river_return_period_years": r["river_flood"]["flood_level_return_period_years"],
            "flood_guide": {k: guide[k] for k in ("prepare_signals", "prepare_within_days", "urgent_within_days",
                                                   "urgent_rain_category", "heavy_rain_days_in_a_row",
                                                   "stay_on_quiet_days")},
            "correction": {"training_days": r["forecast_correction"]["training_days"],
                           "max_shift_c": r["forecast_correction"]["max_shift_c"]},
            "rules_version": rules_version(),
        }

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

    # ---- the agents' own work, already done (no AI per request) -------------------------
    def daily(self) -> dict:
        """This morning's run: the agent on AgentCore wrote a warning for each watched place."""
        if self.daily_store is None:
            return {"status": "not_connected"}
        read_at, cached = self._daily
        if cached is None or self.clock() - read_at > DAILY_SECONDS:
            latest = self.daily_store("latest")
            cached = {"status": "ok" if latest else "not_run_yet", "latest": latest,
                      "history": self.daily_store("index") or []}
            self._daily = (self.clock(), cached)
        return cached

    def agent_replays(self) -> list[dict]:
        out = []
        for path in sorted(AGENT_REPLAYS_DIR.glob("*.json")):
            r = json.loads(path.read_text())
            out.append({k: r[k] for k in ("event_id", "title", "language", "model_id", "event_day", "summary")})
        return out

    def agent_replay(self, replay_id: str) -> dict:
        """A past disaster replayed through the morning warning Graph (evals/eval_agent_replays.py)."""
        path = AGENT_REPLAYS_DIR / f"{replay_id}.json"
        if not re.fullmatch(r"[a-z0-9_]{1,64}", replay_id or "") or not path.is_file():
            raise BadRequest("unknown replay")
        return json.loads(path.read_text())

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
             place: dict | None = None, on_step: Callable[[dict], None] | None = None) -> dict:
        """One chat turn. Everything is checked before the agents run, so a refusal raises before
        on_step is ever called; on_step then hears each tool as it starts."""
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
        team = self._team(session_id, language)
        reply = team.reply(message, on_step=on_step) if on_step else team.reply(message)
        return {**reply, "seconds": round(self.clock() - started, 1)}
