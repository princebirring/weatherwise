"""Kolhapur 2024 replayed through the morning warning Graph, offline (scripted model)."""

from functools import partial

from fake_model import ScriptedModel
from test_backtests import replay

from weatherwise.agents.agent_replay import replay_through_agent
from weatherwise.agents.warning_pipeline import WarningPipeline
from weatherwise.mcp_server.services import backtest_reply
from weatherwise.places.resolve import PlaceContext
from weatherwise.rules import message_policy

EVENT = {"id": "kolhapur_flood_2024_07", "name": "Kolhapur", "lat": 16.70, "lon": 74.24,
         "event_day": "2024-07-26"}
SAFE = ("Heavy rain is likely for several days. Keep documents and medicines in a waterproof bag. "
        "Stay away from rivers and away from hill slopes. Never cross flowing water. Help: 112 / 1077.")
UNSAFE = "Rain of 400 mm is coming. Go to high ground."


def run(script):
    bt, _ = replay("kolhapur_flood_2024_07")
    place = PlaceContext.from_summary(bt.place)
    backtest = backtest_reply(place, bt)
    model = ScriptedModel(script)
    result = replay_through_agent(EVENT, backtest, model, message_policy("in"), "en", "Asia/Kolkata",
                                  make_pipeline=partial(WarningPipeline, with_tone_check=False))
    return result, model


def test_every_morning_code_flagged_gets_a_checked_message_and_quiet_mornings_cost_nothing():
    result, model = run([SAFE] * 40)
    s = result.summary()
    flagged = [m for m in result.mornings if m.code_flagged]
    assert flagged and s["mornings_code_flagged"] == s["mornings_with_checked_message"]
    assert s["first_warning_day"] == "2024-07-17" and s["days_warned_before_event"] == 9
    assert all(m.usage["model_calls"] == 0 for m in result.mornings if not m.code_flagged)
    assert model.calls == s["model_calls"] == len(flagged)  # one draft each, nothing sent back
    assert s["drafts_sent_back_by_evaluator"] == 0 and s["safe_fallbacks_used"] == 0


def test_the_per_event_limit_holds_across_the_replay():
    result, _ = run([SAFE] * 40)
    delivered = [m for m in result.mornings if m.delivered == "send"]
    assert 0 < len(delivered) <= len([m for m in result.mornings if m.code_flagged])


def test_unsafe_drafts_are_sent_back_and_logged_then_the_safe_message_goes_out():
    result, _ = run([UNSAFE] * 3 + [SAFE] * 40)
    first = next(m for m in result.mornings if m.code_flagged)
    assert first.used_fallback and len(first.evaluator_sent_back) == 3
    assert any("high_ground" in rule or "number" in rule for rule in first.evaluator_sent_back[0])
    assert result.summary()["drafts_sent_back_by_evaluator"] == 3
