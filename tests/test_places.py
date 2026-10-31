"""Location-agnostic places: grid cells, terrain, geocoder merging, region lookup, resolve."""

import tomllib
from datetime import date
from pathlib import Path

import pytest

from weatherwise.cache import MemoryCache
from weatherwise.places.geocoding import AdminArea, PlaceCandidate, search_place
from weatherwise.places.grid import grid_cell, neighbour_ring, river_cell
from weatherwise.places.resolve import PlaceResolver
from weatherwise.places.terrain import classify_terrain
from weatherwise.risk.models import TerrainZone
from weatherwise.rules import UnsupportedCountry, country_for

TERRAIN = {"coast_max_km": 20.0, "hills_min_elevation_m": 1000}


class TestGrid:
    def test_weather_cell_snaps_to_quarter_degree(self):
        cell = grid_cell(18.40, 76.56)
        assert (cell.lat, cell.lon) == (18.5, 76.5)

    def test_villages_close_together_share_a_cell(self):
        assert grid_cell(18.40, 76.56).key == grid_cell(18.45, 76.60).key

    def test_river_cell_centres_match_glofas(self):
        cell = river_cell(25.59, 85.14)
        assert (cell.lat, cell.lon) == (25.575, 85.125)

    def test_neighbour_ring_has_eight_cells(self):
        ring = neighbour_ring(grid_cell(18.5, 76.5))
        assert len(ring) == 8 and len({c.key for c in ring}) == 8


class TestTerrain:
    def test_coast_wins_near_the_sea(self):
        assert classify_terrain(2, 2.1, TERRAIN) is TerrainZone.COAST

    def test_hills_by_elevation(self):
        assert classify_terrain(1326, 60.4, TERRAIN) is TerrainZone.HILLS

    def test_plains_otherwise(self):
        assert classify_terrain(638, None, TERRAIN) is TerrainZone.PLAINS


class FakeGeocoder:
    def __init__(self, candidates=None, fail=False):
        self.candidates, self.fail = candidates or [], fail

    def search(self, name, country_code):
        if self.fail:
            raise ConnectionError("down")
        return self.candidates


def candidate(name, lat, lon, district, source="a"):
    return PlaceCandidate(name, lat, lon, AdminArea("in", "Maharashtra", district), source)


class TestSearchPlace:
    def test_merges_sources_and_drops_duplicates(self):
        a = FakeGeocoder([candidate("Wadgaon", 18.10, 76.50, "Latur")])
        b = FakeGeocoder([candidate("Wadgaon", 18.105, 76.505, "Latur", "b"),
                          candidate("Wadgaon", 20.57, 77.24, "Akola", "b")])
        found = search_place("Wadgaon", "in", [a, b])
        assert [c.admin.district for c in found] == ["Latur", "Akola"]

    def test_one_geocoder_down_does_not_block(self):
        found = search_place("Wadgaon", "in", [FakeGeocoder(fail=True),
                                               FakeGeocoder([candidate("Wadgaon", 18.1, 76.5, "Latur")])])
        assert len(found) == 1

    def test_label_reads_back_district_and_state(self):
        assert candidate("Wadgaon", 18.1, 76.5, "Latur").label == "Wadgaon, Latur, Maharashtra"


class TestCountryFor:
    def test_india(self):
        assert country_for("IN") == "in"

    def test_unsupported_country(self):
        with pytest.raises(UnsupportedCountry):
            country_for("zz")


class FakeReverse:
    def __init__(self, admin):
        self.admin = admin

    def reverse(self, lat, lon):
        return self.admin


class FakeCoast:
    def __init__(self, km):
        self.km = km

    def distance_km(self, lat, lon):
        return self.km


class FakeFetch:
    """Stands in for weatherwise.weather.open_meteo inside WeatherService."""

    def __init__(self, elevation, peak_by_cell):
        self.elevation, self.peak_by_cell = elevation, peak_by_cell

    def fetch_elevation(self, lat, lon):
        return self.elevation

    def fetch_river_discharge_many(self, cells, first, last, model):
        return [{"daily": {"river_discharge": [self.peak_by_cell.get((c.lat, c.lon), 1.0)]}}
                for c in cells]

    def fetch_historical_river_discharge(self, cell, first_year, last_year):
        peak = self.peak_by_cell.get((cell.lat, cell.lon), 1.0)
        days = [f"{y}-08-01" for y in range(first_year, last_year + 1)]
        return {"daily": {"time": days, "river_discharge": [peak] * len(days)}}


def resolver(admin, elevation, coast_km, peak_by_cell):
    from weatherwise.weather.service import WeatherService

    cache = MemoryCache()
    r = PlaceResolver(FakeReverse(admin), FakeCoast(coast_km), cache,
                      fetch_timezone=lambda lat, lon: "Asia/Kolkata")
    r.weather_for_tz["Asia/Kolkata"] = WeatherService(cache, "Asia/Kolkata",
                                                      fetch=FakeFetch(elevation, peak_by_cell))
    return r


class TestResolvePlace:
    def test_patna_on_india_defaults_with_ganga_found_in_neighbour_cell(self):
        r = resolver(AdminArea("in", "Bihar", "Patna"), 55, None, {(25.625, 85.125): 45000.0})
        place = r.resolve(25.59, 85.14, today=date(2026, 10, 29))
        assert place.country == "in" and place.timezone == "Asia/Kolkata"
        assert place.terrain is TerrainZone.PLAINS
        assert place.river.is_river_area and place.river.river_lat == 25.625

    def test_small_stream_is_not_a_large_river(self):
        r = resolver(AdminArea("in", "Maharashtra", "Latur"), 638, None, {(18.375, 76.575): 375.0})
        place = r.resolve(18.40, 76.56, today=date(2026, 10, 29))
        assert place.country == "in"
        assert not place.river.is_river_area

    def test_kolhapur_gets_pilot_upstream_points(self):
        r = resolver(AdminArea("in", "Maharashtra", "Kolhapur"), 561, 93.1, {(16.675, 74.275): 1348.0})
        place = r.resolve(16.70, 74.24, today=date(2026, 10, 29))
        assert place.river.is_river_area
        assert len(place.river.upstream_rain_points) == 2
        assert "pilot" in place.river.upstream_source

    def test_coastal_place(self):
        r = resolver(AdminArea("in", "Maharashtra", "Raigad"), 2, 2.1, {})
        assert r.resolve(19.03, 73.07, today=date(2026, 10, 29)).terrain is TerrainZone.COAST

    def test_summary_round_trips(self):
        from weatherwise.places.resolve import PlaceContext

        r = resolver(AdminArea("in", "Maharashtra", "Kolhapur"), 561, 93.1, {(16.675, 74.275): 1348.0})
        place = r.resolve(16.70, 74.24, today=date(2026, 10, 29))
        assert PlaceContext.from_summary(place.summary()) == place


class TestNotCovered:
    """A village outside every country we have rules for gets an honest answer, not a guess."""

    def services(self):
        from weatherwise.mcp_server.services import ClimateRiskServices

        r = resolver(AdminArea("ke", "Kisumu County", "Kisumu"), 1140, None, {})
        r.fetch_timezone = lambda lat, lon: "Africa/Nairobi"
        return ClimateRiskServices(r, geocoders=[], health=None)

    def test_kenyan_village_is_not_covered_and_gets_no_indian_helplines(self):
        s = self.services()
        for answer in (s.resolve_place(-0.10, 34.75), s.hazard_outlook(-0.10, 34.75),
                       s.find_shelters(-0.10, 34.75, "heat")):
            assert answer["covered"] is False and answer["country_code"] == "ke"
            assert answer["covered_countries"] == ["in"]
            assert "1077" not in str(answer) and "helpline" not in answer


FIXTURES = tomllib.loads((Path(__file__).parent / "fixtures" / "places.toml").read_text())["place"]


@pytest.mark.live
@pytest.mark.parametrize("p", FIXTURES, ids=[p["id"] for p in FIXTURES])
def test_live_derivation_matches_expectations(p):
    from weatherwise.mcp_server.services import ClimateRiskServices

    place = ClimateRiskServices.default().resolver.resolve(p["lat"], p["lon"], today=date.today())
    assert place.admin.state == p["expect_state"]
    assert place.admin.district == p["expect_district"]
    assert place.terrain.value == p["expect_terrain"]
    assert place.river.is_river_area == p["expect_river_area"]
    assert len(place.river.upstream_rain_points) == p.get("expect_upstream_points", 0)
