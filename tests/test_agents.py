"""The agent loop end to end with a scripted model: tools, the Evaluator's rewrite loop, the
safe fallback, the cost guard, and the step log. No network, no Bedrock."""

from fake_model import ScriptedModel
from strands import tool

from weatherwise.agents.orchestrator import build_team, fallback_message
from weatherwise.rules import message_policy

OUTLOOK = {
    "place": {"name": "Akola", "district": "Akola", "state": "Maharashtra"},
    "detections": [{"hazard": "excess_heat", "severity": "severe", "first_day": "2026-04-25",
                    "last_day": "2026-04-27", "days_ahead": 3, "agreement": 0.83,
                    "evidence": {"rule": "ours (Excess Heat Factor)", "t95": 35.0}}],
    "flood_guide": {"mode": None, "reasons": []},
    "tmax_forecast_c": 44.0,
}


@tool
def hazard_outlook(lat: float, lon: float, place_name: str | None = None) -> dict:
    """Hazard outlook for a point.

    Args:
        lat: Latitude.
        lon: Longitude.
        place_name: Optional label.
    """
    return OUTLOOK


@tool
def find_place(name: str, country_code: str = "in") -> dict:
    """Find a place by name.

    Args:
        name: Place name.
        country_code: Country.
    """
    return {"candidates": [{"label": "Akola, Akola, Maharashtra", "lat": 20.7, "lon": 77.0}]}


TOOLS = [hazard_outlook, find_place]
POLICY = message_policy("in")
SAFE = "Severe heat likely from Saturday, around 44 °C (83% of forecasts agree). Work before 10 am. Heatstroke: call 108."
UNSAFE = "Severe heat from Saturday, 47 °C. Stay inside."  # made-up 47, no 108


def team(script):
    model = ScriptedModel(script)
    return build_team(model, TOOLS, POLICY, language="en", with_tone_check=False), model


def test_safe_reply_after_tool_call_passes_and_is_logged():
    t, _ = team([("tool", "hazard_outlook", {"lat": 20.7, "lon": 77.0}), SAFE])
    out = t.reply("Is a heat wave coming to Akola?")
    assert out["text"] == SAFE and not out["used_fallback"]
    assert [s["tool"] for s in out["steps"]] == ["hazard_outlook"]


def test_unsafe_reply_is_rewritten():
    t, model = team([("tool", "hazard_outlook", {"lat": 20.7, "lon": 77.0}), UNSAFE, SAFE])
    out = t.reply("Is a heat wave coming to Akola?")
    assert out["text"] == SAFE
    assert model.calls == 3  # tool call, rejected draft, rewrite


def test_repeated_unsafe_replies_fall_back_to_the_safe_message():
    t, _ = team([("tool", "hazard_outlook", {"lat": 20.7, "lon": 77.0}), UNSAFE, UNSAFE, UNSAFE])
    out = t.reply("Is a heat wave coming to Akola?")
    assert out["used_fallback"]
    assert out["text"] == fallback_message(POLICY, "general", "en")
    assert "missing_helpline" in out["violations"]


def test_cost_guard_stops_a_runaway_loop():
    script = [("tool", "find_place", {"name": "Akola"})] * 5 + ["Akola, Maharashtra: is this right?"]
    t, _ = team(script)
    out = t.reply("Akola")
    statuses = [s["status"] for s in out["steps"]]
    assert statuses == ["success"] * 3 + ["error"] * 2  # 4th and 5th calls cancelled by the hook


def test_untranslated_fallback_uses_verified_english():
    assert fallback_message(POLICY, "flood", "ta").startswith("Flood risk")  # no Tamil file yet


def test_fallback_speaks_the_persons_language():
    assert fallback_message(POLICY, "flood", "mr").startswith("तुमच्या भागासाठी पुराचा धोका")
    assert fallback_message(POLICY, "flood", "hi").startswith("आपके इलाके के लिए बाढ़ का खतरा")


def test_orchestrator_has_specialists_and_climate_tools():
    t, _ = team([])
    names = set(t.orchestrator.tool_names)
    assert {"hazard_outlook", "find_place", "warning_agent", "flood_guide_agent"} <= names


APPROVE = {"decision": "approve", "reason": "calm and clear"}
REWRITE = {"decision": "rewrite", "reason": "too alarming; give options"}


def toned_team(script, tone_script):
    model, tone = ScriptedModel(script), ScriptedModel(tone_script)
    return build_team(model, TOOLS, POLICY, language="en", tone_model=tone), model, tone


def test_tone_check_reviews_only_the_final_reply():
    t, _, tone = toned_team([("tool", "hazard_outlook", {"lat": 20.7, "lon": 77.0}), SAFE], [APPROVE])
    out = t.reply("Is a heat wave coming to Akola?")
    assert out["text"] == SAFE
    assert tone.calls == 1  # not once per tool call


def test_tone_check_asks_for_one_rewrite_then_lets_the_safety_rules_decide():
    calmer = SAFE.replace("Work before 10 am.", "You could work before 10 am.")
    t, model, tone = toned_team([("tool", "hazard_outlook", {"lat": 20.7, "lon": 77.0}), SAFE, calmer],
                                [REWRITE, REWRITE])
    out = t.reply("Is a heat wave coming to Akola?")
    assert out["text"] == calmer and model.calls == 3
    assert tone.calls == 1  # the rewrite is accepted without a second tone call
