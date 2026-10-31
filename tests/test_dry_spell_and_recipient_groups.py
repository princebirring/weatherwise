from conftest import ISSUE, forecast

from weatherwise.risk.dry_spell import detect_dry_spell, detect_sowing_risk
from weatherwise.risk.models import Area, Hazard, TerrainZone
from weatherwise.risk.recipient_groups import Subscriber, recipient_groups_for_area

LATUR = Area("latur", "Latur", "Latur", TerrainZone.PLAINS, 18.40, 76.56)


class TestDrySpell:
    def test_forecast_dry_days_join_the_current_spell(self, rules):
        f = forecast([0.0] * 7 + [10.0] * 3)
        found = detect_dry_spell(
            LATUR, f, ISSUE, rules["dry_spell"], in_crop_season=True, past_dry_days=5
        )
        assert len(found) == 1
        assert found[0].hazard is Hazard.DRY_SPELL
        assert found[0].evidence["median_dry_stretch_days"] == 12

    def test_rain_today_ends_the_current_spell(self, rules):
        f = forecast([10.0] + [0.0] * 6 + [10.0] * 3)
        found = detect_dry_spell(
            LATUR, f, ISSUE, rules["dry_spell"], in_crop_season=True, past_dry_days=20
        )
        assert found == []

    def test_outside_crop_season_is_quiet(self, rules):
        f = forecast([0.0] * 14)
        assert detect_dry_spell(LATUR, f, ISSUE, rules["dry_spell"], in_crop_season=False) == []

    def test_wet_soil_is_quiet(self, rules):
        found = detect_dry_spell(
            LATUR, forecast([0.0] * 14), ISSUE, rules["dry_spell"],
            in_crop_season=True, soil_moisture=0.35,
        )
        assert found == []

    def test_light_drizzle_still_counts_as_dry(self, rules):
        found = detect_dry_spell(
            LATUR, forecast([2.4] * 12), ISSUE, rules["dry_spell"], in_crop_season=True
        )
        assert len(found) == 1


class TestSowingRisk:
    def _detect(self, rules, daily_mm):
        return detect_sowing_risk(
            LATUR, forecast([daily_mm] * 14), ISSUE, rules["sowing"],
            in_sowing_window=True, soil_moisture=0.10,
            soil_moisture_dry=rules["dry_spell"]["soil_moisture_dry"],
        )

    def test_dry_soil_and_no_rain_ahead(self, rules):
        assert self._detect(rules, 1.0)[0].severity == "sow_or_wait"

    def test_good_rain_ahead_is_quiet(self, rules):
        assert self._detect(rules, 5.0) == []

    def test_only_checked_in_monsoon_sowing_time(self, rules):
        """After the monsoon every fortnight is dry and crops are sown on stored moisture or
        irrigation, so "wait for rain" would fire daily and be wrong."""
        from datetime import date

        from weatherwise.rules import in_season

        windows = rules["seasons"]["sowing_windows"].values()
        sowing_time = lambda d: any(in_season(d, w) for w in windows)  # noqa: E731
        assert sowing_time(date(2026, 6, 25))
        assert not any(sowing_time(date(2026, m, d)) for m, d in [(10, 20), (10, 31), (11, 15), (11, 30)])


class TestRecipientGroups:
    def test_one_group_per_language_crop_and_water_source(self):
        subscribers = [
            Subscriber("a", ("latur",), "mr", "farmer", "soybean", "well"),
            Subscriber("b", ("latur",), "mr", "farmer", "soybean", "well"),
            Subscriber("c", ("latur",), "hi", "farmer", "soybean", "well"),
            Subscriber("d", ("latur", "beed"), "mr", "household"),
            Subscriber("e", ("beed",), "mr", "farmer", "cotton", "rainfed"),
        ]
        groups = recipient_groups_for_area(subscribers, "latur")
        assert len(groups) == 3
        assert sorted(len(ids) for ids in groups.values()) == [1, 1, 2]
        assert all("e" not in ids for ids in groups.values())
