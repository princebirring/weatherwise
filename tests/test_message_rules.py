"""The Evaluator's code rules (plan §6.1, §8.8.4): every unsafe pattern is caught."""

import pytest

from weatherwise.agents.message_rules import MessageContext, MessageRules, check_message, collect_numbers, numbers_in
from weatherwise.agents.steering import context_from_tools
from weatherwise.rules import message_policy

RULES = MessageRules.from_policy(message_policy("in"))


def rules_broken(text, hazards=(), urgent=False, allowed=()):
    ctx = MessageContext(tuple(hazards), urgent, frozenset(allowed))
    return {v.rule for v in check_message(text, ctx, RULES)}


def test_safe_heat_message_passes():
    text = "Heat wave likely from Friday, about 44 °C (7 of 10 forecasts agree). Work before 10 am. Heatstroke: call 108."
    assert rules_broken(text, ["heat"], allowed={44.0}) == set()


def test_heat_message_without_108_fails():
    assert "missing_helpline" in rules_broken("Very hot days ahead. Stay in shade.", ["heat"])


def test_high_ground_alone_is_unsafe():
    assert "unsafe_high_ground" in rules_broken("Go to high ground now. Call 1077 or 112.", ["flood"])


def test_high_ground_with_slope_warning_is_ok():
    text = "Move to high ground away from hill slopes. Call 1077 or 112."
    assert "unsafe_high_ground" not in rules_broken(text, ["flood"])


def test_marathi_high_ground_alone_is_unsafe():
    assert "unsafe_high_ground" in rules_broken("लगेच उंच जागी जा. 1077 / 112", ["flood"])


def test_no_map_links_in_floods():
    text = "Go to ZP School: https://www.openstreetmap.org/directions?route=1 Call 1077 / 112."
    assert "map_route_in_flood" in rules_broken(text, ["flood"])


def test_map_link_is_fine_for_heat_in_town():
    text = "Nearest cooling center 2 km: https://www.openstreetmap.org/directions?route=1 Heatstroke: call 108."
    assert rules_broken(text, ["heat"], allowed={2.0}) == set()


def test_made_up_number_is_caught():
    assert "unsupported_number" in rules_broken("It will be 47 °C. Call 108.", ["heat"], allowed={44.0})


def test_rounded_numbers_from_tools_are_allowed():
    assert "unsupported_number" not in rules_broken("About 44 °C. Call 108.", ["heat"], allowed={43.6})


def test_urgent_message_must_be_short():
    long_text = "Move to a safe place now away from rivers and hill slopes. " * 8 + "Call 112 / 1077."
    assert "too_long" in rules_broken(long_text, ["flood"], urgent=True)


def test_never_ask_for_otp():
    assert "banned_phrase" in rules_broken("Share the OTP to register. 108", ["heat"])


def test_numbers_need_a_unit_to_be_checked():
    assert numbers_in("Call 1077, it is 44 °C and 120 mm rain, 6 km away") == [44.0, 120.0, 6.0]


def test_collect_numbers_reads_nested_tool_results_and_percentages():
    nums = collect_numbers({"detections": [{"agreement": 0.83, "evidence": {"t95": 35.0}}], "km": [6.2]})
    assert {0.83, 83, 35.0, 6.2} <= nums


@pytest.mark.parametrize("result, expected", [
    ({"detections": [{"hazard": "excess_heat"}], "flood_guide": {"mode": None}}, ("heat",)),
    ({"detections": [], "flood_guide": {"mode": "urgent"}}, ("flood",)),
    ({"place_type": "shelter", "hazard": "flood"}, ("flood", "shelter")),
])
def test_context_is_derived_from_tool_results(result, expected):
    assert context_from_tools([result]).hazards == expected
