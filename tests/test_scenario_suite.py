"""The scenario suite file is well-formed and its checks catch what they should."""

from evals.scenario_checks import check_reply, load_scenarios
from weatherwise.agents.message_rules import MessageRules
from weatherwise.rules import message_policy

RULES = MessageRules.from_policy(message_policy("in"))
CASES = load_scenarios()
REQUIRED = {"id", "title", "part", "lat", "lon", "language", "message", "rubric", "status"}


def test_cases_are_complete_and_unique():
    assert len({c["id"] for c in CASES}) == len(CASES) >= 30
    for c in CASES:
        assert REQUIRED <= set(c), c["id"]
        assert c["status"] in {"pass", "partial", "limit", "out"}


def test_all_three_parts_and_injections_are_covered():
    parts = {c["part"] for c in CASES}
    assert {1, 2, 3} <= parts
    assert sum(c["id"].startswith("INJ") for c in CASES) >= 5


def case(case_id):
    return next(c for c in CASES if c["id"] == case_id)


def test_flood_route_reply_fails_the_check():
    bad = "Go via https://www.openstreetmap.org/directions?route=x to ZP school. Call 1077."
    problems = check_reply(case("A1-09"), bad, ["find_shelters"], RULES)
    assert any("http" in p for p in problems)


def test_good_shelter_reply_passes():
    good = ("No verified cooling center near you. Nearest health facility: PHC Wadgaon. "
            "Heatstroke: call 108. Call 1077 to confirm the place is open.")
    assert check_reply(case("A1-04"), good, ["find_shelters"], RULES) == []


def test_missing_tool_call_fails():
    assert "did not call find_place" in check_reply(case("A1-12"), "Which Wadgaon?", [], RULES)
