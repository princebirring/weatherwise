from conftest import ISSUE, forecast, runs_split

from weatherwise.risk.heavy_rain import detect_heavy_rain, detect_unusual_rain, rain_climate
from weatherwise.risk.models import Area, Hazard, TerrainZone
from weatherwise.risk.river_flood import detect_river_flood

KOLHAPUR = Area("kolhapur", "Kolhapur", "Kolhapur", TerrainZone.PLAINS, 16.70, 74.24)


class TestHeavyRain:
    def test_categories_follow_imd_cutoffs(self, rules):
        f = forecast([10, 64.5, 115.6, 204.5, 64.4])
        found = detect_heavy_rain(KOLHAPUR, f, ISSUE, rules["heavy_rain"])
        assert [d.severity for d in found] == ["heavy", "very_heavy", "extremely_heavy"]
        assert [d.days_ahead for d in found] == [1, 2, 3]

    def test_highest_agreed_category_wins(self, rules):
        # 4 of 10 runs say extremely heavy; all 10 say at least very heavy.
        f = forecast([runs_split(4, 210.0, 120.0)])
        found = detect_heavy_rain(KOLHAPUR, f, ISSUE, rules["heavy_rain"])
        assert found[0].severity == "very_heavy"

    def test_ordinary_rain_is_quiet(self, rules):
        assert detect_heavy_rain(KOLHAPUR, forecast([0, 5, 20]), ISSUE, rules["heavy_rain"]) == []


class TestRiverFlood:
    def test_reports_first_day_above_flood_level(self, rules):
        f = forecast([800, 900, 1600, 1700])
        found = detect_river_flood(KOLHAPUR, f, 1500, ISSUE, rules["river_flood"])
        assert len(found) == 1
        assert found[0].hazard is Hazard.RIVER_FLOOD
        assert found[0].severity == "above_flood_level"
        assert found[0].days_ahead == 2

    def test_needs_half_the_runs(self, rules):
        f = forecast([runs_split(4, 1600.0, 1000.0)])
        assert detect_river_flood(KOLHAPUR, f, 1500, ISSUE, rules["river_flood"]) == []

    def test_below_flood_level_is_quiet(self, rules):
        f = forecast([1400] * 5)
        assert detect_river_flood(KOLHAPUR, f, 1500, ISSUE, rules["river_flood"]) == []


class TestUnusualRain:
    """Ours: rain rare for this place, judged against its own history, not a national line."""

    def test_the_line_is_the_places_own_wettest_days(self):
        history = [0.0] * 990 + [40.0] * 10  # wettest 1% of days: 40 mm
        assert rain_climate(history, percentile=99, min_mm=30.0) == {"unusual_mm": 40.0, "percentile": 99}

    def test_a_dry_place_never_gets_a_line_below_the_minimum(self):
        assert rain_climate([0.0] * 990 + [8.0] * 10, percentile=99, min_mm=30.0)["unusual_mm"] == 30.0

    def test_warns_on_days_enough_runs_reach_the_line(self, rules, akola):
        climate = {"unusual_mm": 45.0, "percentile": 99.5}
        found = detect_unusual_rain(akola, forecast([10, runs_split(5, 50, 20), 10]), climate, ISSUE,
                                    rules["unusual_rain"])
        assert [(d.hazard, d.days_ahead, d.agreement) for d in found] == [(Hazard.UNUSUAL_RAIN, 1, 0.5)]
        assert found[0].evidence["rule"].startswith("ours") and found[0].evidence["threshold_mm"] == 45.0

    def test_below_the_line_is_quiet_even_if_wet(self, rules, akola):
        climate = {"unusual_mm": 85.0, "percentile": 99.5}  # Mumbai: 60 mm is an ordinary wet day
        assert detect_unusual_rain(akola, forecast([60] * 5), climate, ISSUE, rules["unusual_rain"]) == []
