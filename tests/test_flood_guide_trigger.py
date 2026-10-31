"""The safety rule for when a family is told to prepare or to move now (plan §4.3, §6.1)."""

from datetime import timedelta

from conftest import ISSUE

from weatherwise.risk.flood_guide_trigger import (
    PREPARE,
    URGENT,
    FloodGuideDecision,
    decide_flood_guide_mode,
    keep_guide_on,
)
from weatherwise.risk.models import Hazard, HazardDetection


def rain(severity: str, days_ahead: int, place: str = "Ghats") -> HazardDetection:
    return HazardDetection("kolhapur", Hazard.HEAVY_RAIN, severity, ISSUE, ISSUE, days_ahead, 0.7,
                           {"place": place})


def river(days_ahead: int) -> HazardDetection:
    return HazardDetection("kolhapur", Hazard.RIVER_FLOOD, "above_flood_level", ISSUE, ISSUE,
                           days_ahead, 1.0, {"place": "Kolhapur"})


def test_river_model_alone_never_says_move_now(rules):
    assert decide_flood_guide_mode([river(0)], rules["flood_guide"]).mode == PREPARE


def test_very_heavy_rain_upstream_starts_prepare(rules):
    assert decide_flood_guide_mode([rain("very_heavy", 2)], rules["flood_guide"]).mode == PREPARE


def test_heavy_rain_alone_is_not_enough(rules):
    assert decide_flood_guide_mode([rain("heavy", 1)], rules["flood_guide"]).mode is None


def test_extremely_heavy_rain_tomorrow_is_urgent(rules):
    decision = decide_flood_guide_mode([rain("extremely_heavy", 1)], rules["flood_guide"])
    assert decision.mode == URGENT
    assert "Ghats" in decision.reasons[0]


def test_extremely_heavy_rain_later_is_only_prepare(rules):
    assert decide_flood_guide_mode([rain("extremely_heavy", 3)], rules["flood_guide"]).mode == PREPARE


def test_official_red_alert_is_urgent(rules):
    assert decide_flood_guide_mode([], rules["flood_guide"], official_alert="red").mode == URGENT


def test_official_orange_alert_is_prepare(rules):
    assert decide_flood_guide_mode([], rules["flood_guide"], official_alert="orange").mode == PREPARE


def test_signals_beyond_three_days_wait(rules):
    assert decide_flood_guide_mode([river(4), rain("very_heavy", 5)], rules["flood_guide"]).mode is None


class TestGuideStaysOn:
    """Once a household starts preparing, the guide does not vanish because a forecast wobbled."""

    QUIET = FloodGuideDecision(None)

    def test_stays_on_through_quiet_mornings(self, rules):
        for days in range(1, rules["flood_guide"]["stay_on_quiet_days"]):
            kept = keep_guide_on(self.QUIET, ISSUE + timedelta(days=days), ISSUE, rules["flood_guide"])
            assert kept.mode == PREPARE and "staying on" in kept.reasons[0]

    def test_stops_after_enough_quiet_mornings(self, rules):
        n = rules["flood_guide"]["stay_on_quiet_days"]
        assert keep_guide_on(self.QUIET, ISSUE + timedelta(days=n), ISSUE, rules["flood_guide"]).mode is None

    def test_nothing_to_hold_without_an_earlier_signal(self, rules):
        assert keep_guide_on(self.QUIET, ISSUE, None, rules["flood_guide"]).mode is None

    def test_a_fresh_signal_always_wins_and_urgent_is_never_held(self, rules):
        urgent = FloodGuideDecision(URGENT, ["extremely heavy rain tomorrow"])
        assert keep_guide_on(urgent, ISSUE, ISSUE - timedelta(days=2), rules["flood_guide"]) is urgent
        held = keep_guide_on(self.QUIET, ISSUE, ISSUE - timedelta(days=1), rules["flood_guide"])
        assert held.mode == PREPARE  # a held guide is only ever PREPARE, never "move now"
