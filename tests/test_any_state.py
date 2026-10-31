"""Any state works on its country's rules (no state files), including the safety paths that
only run when something has already gone wrong."""

from fake_model import ScriptedModel

from weatherwise.agents.orchestrator import LAST_RESORT, build_team, fallback_message


def test_fallback_never_fails_even_without_a_policy():
    assert fallback_message(None, "heat", "mr") == LAST_RESORT


def test_unknown_language_gets_english(policy):
    assert fallback_message(policy, "flood", "ta").startswith("Flood risk")


def test_chat_team_language_is_the_persons_choice(policy):
    assert build_team(ScriptedModel([]), [], policy, language="mr", with_tone_check=False).language == "mr"
    assert build_team(ScriptedModel([]), [], policy, with_tone_check=False).language == "hi"  # India's default
