"""The WeatherWise API: facts through MCP tools, chat limits, and safe errors (plan §9.2)."""
from starlette.testclient import TestClient

from weatherwise.api.backend import Limits, WeatherWiseApi
from weatherwise.api.server import build_app

SESSION = "s" * 36


class FakeTools:
    def __init__(self):
        self.calls = []

    def __call__(self, name: str, args: dict) -> dict:
        self.calls.append((name, args))
        if name == "message_policy":
            return {"helplines": {"emergency": "112"}, "default_languages": ["hi", "en"]}
        if name == "backtest":
            return {"mode": "as_issued", "timeline": []}
        return {"tool": name}


class FakeTeam:
    def __init__(self, language):
        self.language, self.messages = language, []

    def reply(self, message):
        self.messages.append(message)
        return {"text": f"reply in {self.language}", "used_fallback": False, "violations": [], "steps": []}


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now


def client(team_factory="default", limits=None, clock=None):
    tools = FakeTools()
    teams = []

    def factory(policy, language):
        teams.append(FakeTeam(language))
        return teams[-1]

    backend = WeatherWiseApi(tools, factory if team_factory == "default" else team_factory,
                           limits or Limits(), clock or Clock())
    return TestClient(build_app(backend)), tools, teams


def chat(c, message="Will it be hot?", **extra):
    return c.post("/api/chat", json={"session_id": SESSION, "message": message, "language": "mr", **extra})


def test_place_asks_the_mcp_tools_for_facts_and_outlook():
    c, tools, _ = client()
    body = c.get("/api/place", params={"lat": 16.7, "lon": 74.24}).json()
    assert body == {"place": {"tool": "resolve_place"}, "outlook": {"tool": "hazard_outlook"}}
    assert [n for n, _ in tools.calls] == ["resolve_place", "hazard_outlook"]


def test_bad_coordinates_and_hazards_are_refused():
    c, tools, _ = client()
    assert c.get("/api/place", params={"lat": 120, "lon": 74}).status_code == 400
    assert c.get("/api/shelters", params={"lat": 16, "lon": 74, "hazard": "zombies"}).status_code == 400
    assert tools.calls == []


def test_replays_come_from_the_headline_events_and_are_cached():
    c, tools, _ = client()
    events = c.get("/api/replays").json()
    assert "kolhapur_flood_2024_07" in [r["id"] for r in events]
    for e in events:  # every replay title in every language
        assert set(e["titles"]) == {"en", "hi", "mr"} and all(e["titles"].values())
        assert e["titles"]["mr"] != e["titles"]["en"] and e["titles"]["hi"] != e["titles"]["en"]
    for _ in range(2):
        assert c.get("/api/replays/kolhapur_flood_2024_07").json()["event"]["name"] == "Kolhapur"
    assert [n for n, _ in tools.calls] == ["backtest"]
    assert c.get("/api/replays/nope").status_code == 400


def test_chat_without_agents_says_so_and_rest_still_works():
    c, _, _ = client(team_factory=None)
    assert c.get("/api/status").json()["agents_ready"] is False
    r = chat(c)
    assert r.status_code == 503 and r.json()["error"] == "agents_offline"


def test_chat_uses_one_team_per_session_and_language_with_the_system_place():
    c, _, teams = client()
    place = {"name": "Kolhapur", "lat": 16.7, "lon": 74.24}
    assert chat(c, place=place).json()["text"] == "reply in mr"
    chat(c, "and tomorrow?")
    assert len(teams) == 1 and len(teams[0].messages) == 2
    assert teams[0].messages[0].startswith("[System: the person's saved place is Kolhapur")


def test_long_messages_are_refused_before_the_ai_runs():
    c, _, teams = client(limits=Limits(max_message_chars=10))
    assert chat(c, "x" * 11).status_code == 400
    assert teams == []


def test_rate_limit_per_visitor_then_recovers():
    clock = Clock()
    c, _, _ = client(limits=Limits(chats_per_minute_per_visitor=2), clock=clock)
    assert [chat(c).status_code for _ in range(3)] == [200, 200, 429]
    clock.now += 61
    assert chat(c).status_code == 200


def test_daily_cap_is_the_spend_guard():
    c, _, _ = client(limits=Limits(chats_per_day=1, chats_per_minute_per_visitor=10))
    assert chat(c).status_code == 200
    r = chat(c)
    assert r.status_code == 429 and "busy" in r.json()["message"]


def test_failures_never_leak_internals_and_give_the_helpline():
    def broken(policy, language):
        raise RuntimeError("secret stack detail")

    c, _, _ = client(team_factory=broken)
    r = chat(c)
    assert r.status_code == 502
    assert "secret" not in r.text and "112" in r.json()["message"]


def test_place_outside_covered_countries_is_not_covered_without_helplines():
    class KenyaTools(FakeTools):
        def __call__(self, name, args):
            self.calls.append((name, args))
            return {"covered": False, "country_code": "ke", "covered_countries": ["in"]}

    c = TestClient(build_app(WeatherWiseApi(KenyaTools(), None)))
    for path in ("/api/place?lat=-0.1&lon=34.75", "/api/shelters?lat=-0.1&lon=34.75&hazard=heat"):
        r = c.get(path)
        assert r.status_code == 422 and r.json()["error"] == "not_covered"
        assert r.json()["country_code"] == "ke" and "1077" not in r.text


def test_rate_limit_cannot_be_dodged_by_faking_forwarded_for():
    c, _, _ = client(limits=Limits(chats_per_minute_per_visitor=1))
    fake = {"x-forwarded-for": "1.2.3.4"}
    assert c.post("/api/chat", json={"session_id": SESSION, "message": "hi", "language": "en"}, headers=fake).status_code == 200
    fake = {"x-forwarded-for": "5.6.7.8"}  # a new fake address must not reset the limit
    assert c.post("/api/chat", json={"session_id": SESSION, "message": "hi", "language": "en"}, headers=fake).status_code == 429


def test_cloudfront_viewer_address_identifies_the_visitor(monkeypatch):
    monkeypatch.setenv("WEATHERWISE_BEHIND_CLOUDFRONT", "1")
    c, _, _ = client(limits=Limits(chats_per_minute_per_visitor=1))
    for ip, expected in (("203.0.113.5:4431", 200), ("203.0.113.5:5555", 429), ("198.51.100.9:80", 200)):
        r = c.post("/api/chat", json={"session_id": SESSION, "message": "hi", "language": "en"},
                   headers={"cloudfront-viewer-address": ip})
        assert r.status_code == expected


def test_without_cloudfront_a_faked_viewer_address_does_not_reset_the_limit():
    c, _, _ = client(limits=Limits(chats_per_minute_per_visitor=1))
    send = lambda ip: c.post("/api/chat", json={"session_id": SESSION, "message": "hi", "language": "en"},  # noqa: E731
                             headers={"cloudfront-viewer-address": ip}).status_code
    assert send("203.0.113.5:4431") == 200
    assert send("198.51.100.9:80") == 429


def test_behind_one_trusted_proxy_the_last_forwarded_address_is_the_visitor(monkeypatch):
    monkeypatch.setenv("WEATHERWISE_TRUSTED_PROXY_HOPS", "1")
    c, _, _ = client(limits=Limits(chats_per_minute_per_visitor=1))
    send = lambda xff: c.post("/api/chat", json={"session_id": SESSION, "message": "hi", "language": "en"},  # noqa: E731
                              headers={"x-forwarded-for": xff}).status_code
    assert send("9.9.9.9, 203.0.113.5") == 200
    assert send("1.1.1.1, 203.0.113.5") == 429   # faking the left part changes nothing
    assert send("198.51.100.9") == 200           # a different real visitor


def test_official_warnings_have_their_own_route():
    c, tools, _ = client()
    assert c.get("/api/official", params={"lat": 17.38, "lon": 78.48}).status_code == 200
    assert tools.calls[-1] == ("official_alerts", {"lat": 17.38, "lon": 78.48})
    assert c.get("/api/official", params={"lat": 120, "lon": 78}).status_code == 400
