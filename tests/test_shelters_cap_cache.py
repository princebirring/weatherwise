"""Part 2 shelter router, CAP output, and the cache."""

import threading
import time
from datetime import date
from xml.etree import ElementTree as ET

from weatherwise.cache import FileCache, MemoryCache, cached
from weatherwise.cap import CAP_NS, detection_to_cap
from weatherwise.places.grid import grid_cell
from weatherwise.risk.models import Hazard, HazardDetection
from weatherwise.shelters import OsmHealthFacilities, Shelter, find_shelters, load_shelters

TODAY = date(2026, 4, 20)
HELPLINES = {"disaster": "1077", "ambulance": "108", "emergency": "112"}


def shelter(name, kind, lat, lon, hazards, recheck_due=date(2026, 5, 1)):
    return Shelter(name, kind, lat, lon, hazards, "Latur", "District DM plan p.12", "02382-000000",
                   date(2026, 4, 1), recheck_due)


class FakeHealth:
    def near(self, lat, lon, radius_km):
        return [{"name": "PHC Wadgaon", "lat": lat + 0.05, "lon": lon, "kind": "clinic"}]


class TestShelterRouter:
    def test_heat_returns_nearest_cooling_centers_with_walking_link(self):
        places = [shelter("Town hall", "cooling_center", 18.41, 76.56, ("heat",)),
                  shelter("School", "shelter", 18.40, 76.57, ("flood",))]
        r = find_shelters(18.40, 76.56, "heat", places, HELPLINES, None, TODAY)
        assert [p["name"] for p in r["places"]] == ["Town hall"]
        assert r["places"][0]["directions_link"].startswith("https://www.openstreetmap.org/directions")

    def test_village_with_no_cooling_center_says_so_and_lists_health_facility(self):
        r = find_shelters(18.40, 76.56, "heat", [], HELPLINES, FakeHealth(), TODAY)
        assert r["places"] == []
        assert "No verified cooling center" in r["notes"][0]
        assert r["health_facilities"][0]["source"] == "OpenStreetMap (unverified)"
        assert r["helpline"]["disaster"] == "1077"
        assert (r["search_km"], r["stale_nearby"], r["health_status"]) == (20.0, 0, "ok")

    def test_slow_health_lookup_never_blocks_the_answer(self):
        class SlowOsm(OsmHealthFacilities):
            def download(self, lat, lon, radius_m):
                release.wait(5)
                return [{"name": "PHC Wadgaon", "lat": lat, "lon": lon, "kind": "clinic"}]

        release = threading.Event()
        osm = SlowOsm(MemoryCache(), wait_seconds=0.05)
        started = time.monotonic()
        r = find_shelters(18.40, 76.56, "heat", [], HELPLINES, osm, TODAY)
        assert time.monotonic() - started < 1
        assert r["health_facilities"] == [] and r["helpline"]["disaster"] == "1077"
        assert r["health_status"] == "unavailable"
        assert any("call 108" in n for n in r["notes"])

        release.set()  # the download finishes in the background and fills the cache
        for _ in range(50):
            if osm.cache.get("health_facilities", f"{grid_cell(18.40, 76.56).key}:20.0") is not None:
                break
            time.sleep(0.02)
        again = find_shelters(18.40, 76.56, "heat", [], HELPLINES, osm, TODAY)
        assert again["health_facilities"][0]["name"] == "PHC Wadgaon"

    def test_second_asker_does_not_wait_and_failures_are_not_retried_at_once(self):
        class FailingOsm(OsmHealthFacilities):
            calls = 0

            def download(self, lat, lon, radius_m):
                FailingOsm.calls += 1
                gate.wait(5)
                raise ConnectionError("all mirrors down")

        gate = threading.Event()
        osm = FailingOsm(MemoryCache(), wait_seconds=0.05)
        find_shelters(18.40, 76.56, "heat", [], HELPLINES, osm, TODAY)  # starts the download
        started = time.monotonic()
        find_shelters(18.40, 76.56, "heat", [], HELPLINES, osm, TODAY)  # download still running
        assert time.monotonic() - started < 0.04
        gate.set()
        for _ in range(50):
            if not osm._running:
                break
            time.sleep(0.02)
        r = find_shelters(18.40, 76.56, "heat", [], HELPLINES, osm, TODAY)  # just failed: no retry
        assert FailingOsm.calls == 1
        assert any("call 108" in n for n in r["notes"])

    def test_flood_never_gives_a_map_route(self):
        places = [shelter("ZP school", "shelter", 16.71, 74.24, ("flood",))]
        r = find_shelters(16.70, 74.24, "flood", places, HELPLINES, None, TODAY)
        assert r["places"][0]["directions_link"] is None
        assert any("Never walk or drive through flowing water" in n for n in r["notes"])

    def test_overdue_shelter_is_hidden(self):
        places = [shelter("Old hall", "cooling_center", 18.41, 76.56, ("heat",), date(2026, 4, 1))]
        r = find_shelters(18.40, 76.56, "heat", places, HELPLINES, None, TODAY)
        assert r["places"] == []
        assert any("overdue for re-checking" in n for n in r["notes"])

    def test_rows_missing_acceptance_fields_are_rejected(self, tmp_path):
        (tmp_path / "shelters_xx.csv").write_text(
            "name,type,lat,lon,hazards,district,source,contact,open_status,checked_on,checked_by,recheck_due\n"
            "Good,shelter,1,2,flood,D,DM plan,1,open,2026-04-01,me,2026-05-01\n"
            "No source,shelter,1,2,flood,D,,1,open,2026-04-01,me,2026-05-01\n")
        assert [s.name for s in load_shelters("xx", root=tmp_path)] == ["Good"]


class TestCap:
    def test_valid_cap_with_honest_sender(self):
        d = HazardDetection("akola", Hazard.EXCESS_HEAT, "severe", date(2026, 4, 25),
                            date(2026, 4, 27), 3, 0.83, {"rule": "ours (Excess Heat Factor)"})
        xml = detection_to_cap(d, "Akola, Maharashtra", 20.7, 77.0, "Asia/Kolkata",
                               "Excess heat expected", "Stay indoors 12-4 pm. Call 108 for heatstroke.")
        root = ET.fromstring(xml)
        ns = {"c": CAP_NS}
        assert root.find("c:status", ns).text == "Exercise"
        info = root.find("c:info", ns)
        assert info.find("c:urgency", ns).text == "Future"
        assert info.find("c:severity", ns).text == "Severe"
        assert info.find("c:certainty", ns).text == "Likely"
        assert "not an official warning service" in info.find("c:senderName", ns).text
        assert info.find("c:area/c:circle", ns).text == "20.7000,77.0000 15.0"


class TestCache:
    def test_expired_entries_read_as_missing(self, tmp_path):
        clock = [1000.0]
        cache = FileCache(tmp_path, now=lambda: clock[0])
        cache.put("forecast", "cell", {"x": 1})
        assert cache.get("forecast", "cell") == {"x": 1}
        clock[0] += 4 * 3600  # forecasts live 3 hours
        assert cache.get("forecast", "cell") is None

    def test_cached_computes_once(self, tmp_path):
        cache, calls = FileCache(tmp_path), []
        for _ in range(3):
            cached(cache, "normals", "cell", lambda: calls.append(1) or 42)
        assert len(calls) == 1
