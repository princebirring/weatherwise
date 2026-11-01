"""Rules: global -> country, per-language safety text, and the message_policy the MCP server serves."""

import shutil
from pathlib import Path

import pytest

from weatherwise.rules import (
    RULES_ROOT,
    ConfigError,
    load_rules,
    message_policy,
    supported_countries,
    supported_languages,
)


@pytest.fixture
def policy_with_untranslated_language(tmp_path):
    """The real rules plus a language whose translations are not verified yet."""
    root = tmp_path / "rules"
    shutil.copytree(RULES_ROOT, root)
    (root / "languages" / "ta.toml").write_text(
        '[safe_messages]\nflood = "TODO(user)"\n[footer]\ntext = "TODO(user)"\n'
        '[guidance]\nflood_urgent = "TODO(user)"\nheat = [{ who = "TODO", what = "TODO" }]\n')
    return message_policy("in", root=root)


def test_country_gets_global_and_official_values(rules):
    assert rules["heat"]["min_agreement"] == 0.70            # global (ours)
    assert rules["heat"]["rule"] == "imd"                    # country (official)
    assert rules["heavy_rain"]["very_heavy"] == 115.6        # country (official)
    assert rules["flood_guide"]["prepare_within_days"] == 3  # global (ours)


def test_country_overrides_global(tmp_path):
    (tmp_path / "countries").mkdir()
    (tmp_path / "global.toml").write_text("[heat]\nmin_agreement = 0.7\nmin_consecutive_days = 2\n")
    (tmp_path / "countries" / "xx.toml").write_text('[heat]\nrule = "imd"\nmin_agreement = 0.8\n')
    merged = load_rules("xx", root=tmp_path, validate=False)
    assert merged["heat"] == {"min_agreement": 0.8, "min_consecutive_days": 2, "rule": "imd"}


def test_missing_rules_fail_at_load_not_at_6_am(tmp_path):
    (tmp_path / "countries").mkdir()
    (tmp_path / "countries" / "xx.toml").write_text("[heat]\nmin_agreement = 0.7\n")
    with pytest.raises(ConfigError, match=r"\[helplines\] emergency"):
        load_rules("xx", root=tmp_path)


@pytest.mark.parametrize("country", supported_countries())
def test_every_country_is_complete(country):
    load_rules(country)


def country_with(tmp_path, extra: str) -> Path:
    """The real rules, plus a test country "xx" with India's file and extra lines appended."""
    shutil.copytree(RULES_ROOT, tmp_path / "rules")
    india = (tmp_path / "rules" / "countries" / "in.toml").read_text()
    (tmp_path / "rules" / "countries" / "xx.toml").write_text(india + "\n" + extra)
    return tmp_path / "rules"


def test_a_country_can_switch_a_check_off(tmp_path):
    root = country_with(tmp_path, '[checks]\nenabled = ["heat_wave", "heavy_rain"]\n')
    assert load_rules("xx", root=root)["checks"]["enabled"] == ["heat_wave", "heavy_rain"]


@pytest.mark.parametrize("extra, message", [
    ('[checks]\nenabled = ["heat_wave", "humid_heat"]\n', "humid_heat"),
    ('[flood_guide]\nprepare_signals = ["very_heavy_rian"]\n', "very_heavy_rian"),
    ('[work_heat]\nlevels = [{ name = "danger" }]\n', r"\[work_heat\] levels"),
])
def test_a_misspelt_switch_fails_at_load_never_silently_off(tmp_path, extra, message):
    with pytest.raises(ConfigError, match=message):
        load_rules("xx", root=country_with(tmp_path, extra))


def test_no_state_or_time_zone_settings_remain(rules):
    assert "locale" not in rules and "admin" not in rules


class TestMessagePolicy:
    def test_unsafe_phrases_cover_every_language(self, policy):
        phrases = policy["messages"]["high_ground_phrases"]
        assert {"high ground", "उंच जागी", "ऊंची जगह"} <= set(phrases)

    def test_unverified_translations_fall_back_to_english(self, policy_with_untranslated_language):
        p = policy_with_untranslated_language
        assert p["safe_messages"]["ta"]["flood"] == p["safe_messages"]["en"]["flood"]
        assert p["footer"]["ta"] == p["footer"]["en"]

    def test_every_language_has_every_safe_message(self, policy):
        for lang in supported_languages():
            assert all(policy["safe_messages"][lang][k] for k in ("general", "heat", "flood"))

    def test_website_guidance_falls_back_to_english(self, policy_with_untranslated_language):
        p = policy_with_untranslated_language
        en = p["guidance"]["en"]
        assert set(p["guidance"]["ta"]) == set(en)
        assert p["guidance"]["ta"]["flood_urgent"] == en["flood_urgent"]
        assert p["guidance"]["ta"]["heat"] == en["heat"]  # one TODO item: the whole list falls back

    def test_every_language_has_its_own_complete_guidance(self, policy):
        """Full language switch: Hindi and Marathi carry every key, in the same shape as English."""
        en = policy["guidance"]["en"]
        for lang in ("hi", "mr"):
            g = policy["guidance"][lang]
            assert set(g) == set(en)
            for key, value in en.items():
                assert g[key] != value, f"{lang}.{key} is still English"
                if isinstance(value, list):
                    assert len(g[key]) == len(value), f"{lang}.{key} has a different number of steps"
                    if value and isinstance(value[0], dict):
                        assert all(set(item) == {"who", "what"} for item in g[key])

    def test_every_language_has_its_own_safe_messages_and_footer(self, policy):
        for lang in ("hi", "mr"):
            for kind in ("general", "heat", "flood"):
                assert policy["safe_messages"][lang][kind] != policy["safe_messages"]["en"][kind]
                assert all(n in policy["safe_messages"][lang][kind] for n in ("112", "1077") if kind != "heat")
            assert policy["footer"][lang] != policy["footer"]["en"]

    def test_website_guidance_never_says_high_ground_without_slopes(self, policy):
        rules = policy["messages"]
        for guidance in policy["guidance"].values():
            for value in guidance.values():
                items = [value] if isinstance(value, str) else value
                for item in items:
                    text = " ".join(item.values()) if isinstance(item, dict) else item
                    if any(p in text.lower() for p in rules["high_ground_phrases"]):
                        assert any(w in text.lower() for w in rules["slope_safety_words"]), text

    def test_website_flood_line_matches_the_shelter_tool(self, policy):
        from weatherwise.shelters import FLOOD_SAFETY_LINE

        assert policy["guidance"]["en"]["flood_safety_line"] == FLOOD_SAFETY_LINE

    def test_carries_helplines_and_version(self, policy):
        assert policy["helplines"]["disaster"] == "1077"
        assert len(policy["rules_version"]) == 12
