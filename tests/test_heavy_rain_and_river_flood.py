from conftest import ISSUE, forecast, runs_split

from weatherwise.risk.heavy_rain import detect_heavy_rain
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
