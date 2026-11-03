"""The WeatherWise API: facts through MCP tools, chat limits, and safe errors (plan §9.2)."""
from starlette.testclient import TestClient

from weatherwise.api.agentcore import AgentCoreTeamFactory
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


class FakeRuntimeBody:
    def __init__(self, result):
        self.result, self.closed = result, False

    def read(self):
        import json

        return json.dumps(self.result).encode()

    def close(self):
        self.closed = True


class FakeRuntimeClient:
    def __init__(self, text="AgentCore reply"):
        self.calls = []
        self.text = text

    def invoke_agent_runtime(self, **kwargs):
        self.calls.append(kwargs)
        return {"response": FakeRuntimeBody({"text": self.text, "used_fallback": False,
                                               "violations": [], "steps": []})}


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


def test_place_search_in_the_persons_language():
    c, tools, _ = client()
    assert c.get("/api/places", params={"q": "Akola", "lang": "mr"}).status_code == 200
    assert tools.calls[-1] == ("find_place", {"name": "Akola", "language": "mr"})
    c.get("/api/places", params={"q": "Akola"})
    assert tools.calls[-1] == ("find_place", {"name": "Akola"})   # English: unchanged call
    assert c.get("/api/places", params={"q": "Akola", "lang": "xx"}).status_code == 400


def test_rules_summary_comes_from_the_rules_files():
    from weatherwise.rules import load_rules
    c, _, _ = client()
    body = c.get("/api/rules").json()
    r = load_rules("in")
    assert body["rain_mm"]["very_heavy"] == r["heavy_rain"]["very_heavy"]
    assert body["heat"]["departure_c"] == r["heat"]["heat_wave_departure"]
    assert body["heat"]["work_heat_c"] == {lv["name"]: lv["feels_like_c"] for lv in r["work_heat"]["levels"]}
    assert body["flood_guide"]["prepare_signals"] == r["flood_guide"]["prepare_signals"]


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


def test_chat_can_delegate_to_a_private_agentcore_runtime():
    runtime = FakeRuntimeClient()
    backend = WeatherWiseApi(FakeTools(), AgentCoreTeamFactory(runtime, "arn:runtime/weatherwise"))
    c = TestClient(build_app(backend))
    response = chat(c, place={"name": "Phagwara", "lat": 31.224, "lon": 75.773})

    assert response.status_code == 200 and response.json()["text"] == "AgentCore reply"
    call = runtime.calls[0]
    assert call["agentRuntimeArn"] == "arn:runtime/weatherwise"
    assert call["runtimeSessionId"]
    import json

    payload = json.loads(call["payload"])
    assert payload["type"] == "chat" and payload["language"] == "mr"
    assert "saved place is Phagwara" in payload["message"]


def test_agentcore_reasoning_tags_are_not_returned_to_the_browser():
    runtime = FakeRuntimeClient("<thinking>private model notes</thinking><response>Safe public reply</response>")
    backend = WeatherWiseApi(FakeTools(), AgentCoreTeamFactory(runtime, "arn:runtime/weatherwise"))
    response = TestClient(build_app(backend)).post("/api/chat", json={
        "session_id": SESSION, "message": "hi", "language": "en",
    })

    assert response.status_code == 200 and response.json()["text"] == "Safe public reply"


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


def test_the_morning_run_is_read_from_the_store_and_reused_for_five_minutes():
    reads, clock = [], Clock()

    def store(name):
        reads.append(name)
        return {"run_date": "2026-11-03", "summary": {"places": 25}} if name == "latest" else [{"run_date": "2026-11-03"}]
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), None, clock=clock, daily_store=store)))
    first = c.get("/api/daily").json()
    assert first["status"] == "ok" and first["latest"]["summary"]["places"] == 25 and len(first["history"]) == 1
    c.get("/api/daily")
    assert reads == ["latest", "index"]
    clock.now += 301
    c.get("/api/daily")
    assert reads == ["latest", "index", "latest", "index"]


def test_no_morning_run_yet_and_no_store_are_said_plainly():
    assert TestClient(build_app(WeatherWiseApi(FakeTools(), None))).get("/api/daily").json() == {"status": "not_connected"}
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), None, daily_store=lambda name: None)))
    assert c.get("/api/daily").json()["status"] == "not_run_yet"


def test_agent_replays_refuse_unknown_or_odd_ids(tmp_path, monkeypatch):
    import json

    from weatherwise.api import backend as b
    monkeypatch.setattr(b, "AGENT_REPLAYS_DIR", tmp_path)
    (tmp_path / "kolhapur_flood_2024_07.json").write_text(json.dumps({
        "event_id": "kolhapur_flood_2024_07", "title": "Kolhapur", "language": "mr", "model_id": "m",
        "event_day": "2024-07-26", "summary": {"days_warned_before_event": 9}, "mornings": []}))
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), None)))
    assert c.get("/api/agent-replays").json()[0]["summary"]["days_warned_before_event"] == 9
    assert c.get("/api/agent-replays/kolhapur_flood_2024_07").json()["mornings"] == []
    for bad in ("nope", "..%2Fsecrets", "Kolhapur"):
        assert c.get(f"/api/agent-replays/{bad}").status_code in (400, 404)


class FakeEventStream:
    def __init__(self, events):
        self.events, self.closed = events, False

    def iter_lines(self):
        import json

        for e in self.events:
            yield f"data: {json.dumps(e)}".encode()
            yield b""

    def close(self):
        self.closed = True


class FakeStreamingRuntime:
    """A runtime that streams, like the one on AgentCore: steps, then the reply."""

    def __init__(self, events=None):
        self.calls = []
        self.events = events or [
            {"type": "step", "agent": "orchestrator", "tool": "hazard_outlook"},
            {"type": "step", "agent": "orchestrator", "tool": "warning_agent"},
            {"type": "reply", "text": "Severe heat from Saturday.", "used_fallback": False, "violations": [], "steps": []},
        ]

    def invoke_agent_runtime(self, **kwargs):
        self.calls.append(kwargs)
        return {"contentType": "text/event-stream", "response": FakeEventStream(self.events)}


def stream_chat(c, message="Will it be hot?", **extra):
    import json

    r = c.post("/api/chat", headers={"accept": "application/x-ndjson"},
               json={"session_id": SESSION, "message": message, "language": "mr", **extra})
    return r, [json.loads(line) for line in r.text.splitlines() if line] if r.status_code == 200 else []


def test_chat_streams_each_agent_step_then_the_checked_reply():
    runtime = FakeStreamingRuntime()
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), AgentCoreTeamFactory(runtime, "arn:runtime/weatherwise"))))
    r, events = stream_chat(c)

    assert r.headers["content-type"].startswith("application/x-ndjson")
    assert [(e["type"], e.get("tool")) for e in events] == [
        ("step", "hazard_outlook"), ("step", "warning_agent"), ("reply", None)]
    assert events[-1]["text"] == "Severe heat from Saturday." and "seconds" in events[-1]
    assert "text/event-stream" in runtime.calls[0]["accept"]


def test_plain_json_chat_still_works_with_a_streaming_runtime():
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), AgentCoreTeamFactory(FakeStreamingRuntime(), "arn:rt"))))
    assert chat(c).json()["text"] == "Severe heat from Saturday."


def test_follow_ups_send_the_conversation_so_far_so_a_restarted_session_remembers():
    import json

    runtime = FakeStreamingRuntime()
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), AgentCoreTeamFactory(runtime, "arn:rt"))))
    chat(c, "Will it be hot?")
    chat(c, "What about my cows?")

    first, second = (json.loads(call["payload"]) for call in runtime.calls)
    assert first["history"] == []
    assert second["history"] == [{"role": "user", "text": "Will it be hot?"},
                                 {"role": "assistant", "text": "Severe heat from Saturday."}]
    assert runtime.calls[0]["runtimeSessionId"] == runtime.calls[1]["runtimeSessionId"]


def test_streamed_chat_refusals_keep_their_status_code():
    c, _, teams = client(limits=Limits(max_message_chars=10))
    r, _ = stream_chat(c, "x" * 11)
    assert r.status_code == 400 and r.json()["error"] == "bad_request" and teams == []
    c, _, _ = client(team_factory=None)
    assert stream_chat(c)[0].status_code == 503


def test_a_runtime_failure_mid_stream_gives_the_helpline_not_the_details():
    runtime = FakeStreamingRuntime([
        {"type": "step", "agent": "orchestrator", "tool": "hazard_outlook"},
        {"error": "secret stack detail", "error_type": "RuntimeError", "message": "An error occurred during streaming"},
    ])
    c = TestClient(build_app(WeatherWiseApi(FakeTools(), AgentCoreTeamFactory(runtime, "arn:rt"))))
    r, events = stream_chat(c)

    assert [e["type"] for e in events] == ["step", "error"]
    assert "secret" not in r.text and "112" in events[-1]["message"]


def test_the_real_agent_team_streams_its_steps_through_the_api():
    from fake_model import ScriptedModel
    from test_agents import POLICY, SAFE, TOOLS

    from weatherwise.agents.orchestrator import build_team

    def factory(policy, language):
        model = ScriptedModel([("tool", "hazard_outlook", {"lat": 20.7, "lon": 77.0}), SAFE])
        return build_team(model, TOOLS, POLICY, language="en", with_tone_check=False)

    c = TestClient(build_app(WeatherWiseApi(FakeTools(), factory)))
    _, events = stream_chat(c, "Is a heat wave coming to Akola?")
    assert [(e["type"], e.get("tool"), e.get("done")) for e in events] == [
        ("step", "hazard_outlook", False), ("step", "hazard_outlook", True), ("reply", None, None)]
    assert events[-1]["text"] == SAFE
