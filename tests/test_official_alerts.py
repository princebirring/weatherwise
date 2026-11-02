"""Official warnings from SACHET: parsed, current, translated, and never silently missing."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from weatherwise.cache import MemoryCache
from weatherwise.mcp_server import services as svc
from weatherwise.official.sachet import IST, SachetAlerts, most_serious, parse_alert
from weatherwise.places.geocoding import AdminArea
from weatherwise.risk.area_scan import ScanResult
from weatherwise.risk.flood_guide_trigger import decide_flood_guide_mode
from weatherwise.risk.models import Area, TerrainZone
from weatherwise.rules import load_rules

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "sachet_location_alerts.json").read_text())
EVENING = datetime(2026, 10, 31, 20, 0, tzinfo=IST)  # both fixture alerts in force


class FakeSachet:
    """SACHET's two calls: alerts for a point (the saved real answer) and translation."""

    def __init__(self, alerts=None, translate_ok=True, down=False):
        self.alerts = FIXTURE["alerts"] if alerts is None else alerts
        self.translate_ok, self.down = translate_ok, down
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, path: str, params: dict) -> dict:
        self.calls.append((path, params))
        if self.down:
            raise ConnectionError("SACHET unreachable")
        if path == "FetchLocationWiseAlerts":
            return {"alerts": self.alerts}
        if path == "FetchTextTranslation":
            if not self.translate_ok:
                return {"response": "Failure"}
            return {"response": "Success", "body": f"[{params['targetLang']}] {params['text']}"}
        raise AssertionError(path)


def alerts(fake: FakeSachet, now=EVENING, lat=17.384, lon=78.4866) -> dict:
    return SachetAlerts(MemoryCache(), post=fake, now=lambda: now).for_point(lat, lon)


def test_parses_the_real_answer_most_serious_first():
    out = alerts(FakeSachet())
    assert out["status"] == "ok"
    first, second = out["alerts"]
    assert (first["event"], first["level"], first["level_word"], first["source"], first["language"]) == (
        "Lightning", "orange", "ALERT", "Andhra Pradesh SDMA", "te")
    assert (second["level"], second["source"]) == ("yellow", "Telangana SDMA")
    assert second["ends"] == "2026-11-01T08:31:00+05:30"


def test_every_alert_comes_in_every_website_language_and_keeps_the_original():
    telugu = alerts(FakeSachet())["alerts"][0]
    assert set(telugu["translations"]) == {"te", "en", "hi", "mr"}
    assert telugu["translations"]["te"] == telugu["message"]
    assert telugu["translations"]["mr"].startswith("[mr] ")


def test_failed_translation_still_shows_the_original():
    out = alerts(FakeSachet(translate_ok=False))["alerts"]
    assert len(out) == 2
    assert set(out[0]["translations"]) == {"te"}


def test_expired_alerts_are_dropped():
    next_noon = datetime(2026, 11, 1, 12, 0, tzinfo=IST)  # the Telangana watch ended at 08:31
    assert [a["source"] for a in alerts(FakeSachet(), now=next_noon)["alerts"]] == ["Andhra Pradesh SDMA"]


def test_unreachable_is_reported_never_read_as_no_warnings():
    out = alerts(FakeSachet(down=True))
    assert out == {"status": "unavailable", "alerts": [], "source": out["source"]}


def test_asks_for_the_point_rounded_to_about_a_kilometre_and_caches_it():
    fake = FakeSachet(translate_ok=False)
    source = SachetAlerts(MemoryCache(), post=fake, now=lambda: EVENING)
    source.for_point(17.38449, 78.48661)
    source.for_point(17.38449, 78.48661)
    asks = [p for path, p in fake.calls if path == "FetchLocationWiseAlerts"]
    assert asks == [{"lat": 17.38, "long": 78.49, "radius": 20}]


def test_the_same_warning_for_overlapping_areas_shows_once_the_longest():
    first = FIXTURE["alerts"][1]
    repeat = {**first, "identifier": 999, "effective_end_time": "Sun Nov 01 06:40:00 IST 2026"}
    out = alerts(FakeSachet(alerts=[repeat, first], translate_ok=False))["alerts"]
    assert len(out) == 1 and out[0]["ends"] == "2026-11-01T17:10:00+05:30"


def test_a_malformed_alert_does_not_hide_the_others():
    broken = {**FIXTURE["alerts"][0], "effective_end_time": "not a date"}
    out = alerts(FakeSachet(alerts=[broken, FIXTURE["alerts"][1]], translate_ok=False))["alerts"]
    assert [a["source"] for a in out] == ["Andhra Pradesh SDMA"]


class TestFloodGuideUsesOnlyFloodAlerts:
    def alert(self, event: str, colour: str) -> dict:
        raw = {**FIXTURE["alerts"][0], "disaster_type": event, "severity_color": colour}
        return {"level": colour, "flood_related": parse_alert(raw).flood_related}

    def test_lightning_never_starts_the_flood_guide(self):
        assert most_serious([self.alert("Lightning", "red")], flood_only=True) is None

    @pytest.mark.parametrize("event", ["Heavy Rain", "Flood", "Cyclone", "Deep Depression", "Storm Surge"])
    def test_flood_rain_and_cyclone_alerts_do(self, event):
        found = [self.alert("Lightning", "red"), self.alert(event, "orange")]
        assert most_serious(found, flood_only=True) == "orange"

    def test_most_serious_colour_wins(self):
        assert most_serious([self.alert("Flood", "yellow"), self.alert("Flood", "red")]) == "red"


class TestOutlookPutsOfficialWarningsFirst:
    """hazard_outlook carries the official warnings, and an official red flood alert makes the
    flood guide urgent, even when our own forecast sees nothing."""

    def services(self, monkeypatch, alerts_answer, provider="sachet"):
        class Place:
            name, country, timezone = "Kakinada", "in", "Asia/Kolkata"
            admin = AdminArea("in", "Andhra Pradesh", "Kakinada")
            terrain = TerrainZone.COAST
            river = type("River", (), {"is_river_area": False, "flood_level_m3s": None})()
            cell = type("Cell", (), {"key": "0.25:17.0:82.25"})()

            def as_area(self):
                return Area("kakinada", self.name, "Kakinada", self.terrain, 16.99, 82.25)

        rules = load_rules("in")
        if provider is None:
            rules = {k: v for k, v in rules.items() if k != "official_alerts"}
        seen = {}

        def scan(area, weather, today, rules, official_alert=None):
            seen["official_alert"] = official_alert
            result = ScanResult(area, today)
            result.flood_guide = decide_flood_guide_mode([], rules["flood_guide"], official_alert)
            return result

        monkeypatch.setattr(svc, "fetch_raw_inputs", lambda *a: {})
        monkeypatch.setattr(svc, "build_area_weather", lambda *a: type("W", (), {"correction": {}})())
        monkeypatch.setattr(svc, "daily_outlook", lambda *a, **k: [])
        monkeypatch.setattr(svc, "scan_area", scan)
        official = type("Official", (), {"for_point": lambda self, lat, lon: alerts_answer})()
        s = svc.ClimateRiskServices(resolver=type("Res", (), {"weather": lambda self, tz: None})(),
                                    geocoders=[], health=None, official=official)
        monkeypatch.setattr(s, "_place", lambda lat, lon, name=None: (Place(), rules, EVENING.date()))
        return s, seen

    def flood_alert(self, colour):
        return {"level": colour, "flood_related": True, "event": "Heavy Rain"}

    def test_official_red_flood_alert_makes_the_guide_urgent(self, monkeypatch):
        answer = {"status": "ok", "alerts": [self.flood_alert("red")], "source": "SACHET"}
        s, seen = self.services(monkeypatch, answer)
        out = s.hazard_outlook(16.99, 82.25)
        assert seen["official_alert"] == "red"
        assert out["flood_guide"]["mode"] == "urgent" and out["official"] == answer

    def test_official_orange_flood_alert_starts_prepare(self, monkeypatch):
        s, _ = self.services(monkeypatch, {"status": "ok", "alerts": [self.flood_alert("orange")], "source": "S"})
        assert s.hazard_outlook(16.99, 82.25)["flood_guide"]["mode"] == "prepare"

    def test_country_without_an_official_feed_says_not_connected(self, monkeypatch):
        s, seen = self.services(monkeypatch, {"status": "ok", "alerts": [self.flood_alert("red")]}, provider=None)
        out = s.hazard_outlook(16.99, 82.25)
        assert out["official"]["status"] == "not_connected" and seen["official_alert"] is None


class TestOfficialWarningsDoNotDependOnTheForecast:
    """The weather service can be down or rate-limited; official warnings must still show."""

    def services(self, country_code: str, alerts_answer: dict, admin_fails: bool = False):
        class Resolver:
            def admin(self, lat, lon):
                if admin_fails:
                    raise ConnectionError("map service down")
                return AdminArea(country_code, "Telangana", "Hyderabad")

            def resolve(self, *a, **k):
                raise AssertionError("official warnings must not need the forecast-side place lookup")

        official = type("Official", (), {"for_point": lambda self, lat, lon: alerts_answer})()
        return svc.ClimateRiskServices(resolver=Resolver(), geocoders=[], health=None, official=official)

    def test_official_warnings_need_only_the_country(self):
        answer = {"status": "ok", "alerts": [{"level": "yellow"}], "source": "SACHET"}
        out = self.services("in", answer).official_alerts(17.38, 78.48)
        assert out["status"] == "ok" and out["alerts"] == answer["alerts"] and out["covered"] is True

    def test_place_lookup_down_is_unavailable_never_none(self):
        out = self.services("in", {}, admin_fails=True).official_alerts(17.38, 78.48)
        assert out["status"] == "unavailable" and out["alerts"] == []

    def test_country_we_do_not_cover(self):
        out = self.services("ke", {}).official_alerts(-0.10, 34.75)
        assert out["covered"] is False and "1077" not in str(out)


@pytest.mark.live
def test_live_sachet_answers_for_a_point():
    out = SachetAlerts(MemoryCache()).for_point(17.38, 78.48)  # Hyderabad
    assert out["status"] == "ok"
    for alert in out["alerts"]:
        assert alert["level"] in {"red", "orange", "yellow", "green"} and alert["source"] and alert["ends"]
        assert alert["translations"][alert["language"]] == alert["message"]
