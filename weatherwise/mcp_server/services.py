"""ClimateRiskServices: the one code path behind the MCP tools, scripts and agents.

Every method takes a point (or a name to geocode) and returns plain JSON-ready dicts.
External services are injected, so production swaps Nominatim for Amazon Location and the
file cache for DynamoDB/S3 without changing this file.
"""

import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from weatherwise.backtest.backtest import backtest_place
from weatherwise.backtest.verification import verify
from weatherwise.cache import Cache, FileCache, LayeredCache, S3Cache, cached
from weatherwise.cap import detection_to_cap
from weatherwise.official.sachet import SachetAlerts, most_serious
from weatherwise.places.geocoding import Geocoder, NominatimGeocoder, OpenMeteoGeocoder, search_place
from weatherwise.places.resolve import PlaceContext, PlaceResolver
from weatherwise.places.terrain import Coastline
from weatherwise.risk.area_scan import daily_outlook, scan_area
from weatherwise.risk.models import Hazard, HazardDetection
from weatherwise.rules import (
    UnsupportedCountry,
    country_for,
    load_rules,
    message_policy,
    rules_version,
    supported_countries,
)
from weatherwise.shelters import HealthFacilityFinder, OsmHealthFacilities, find_shelters, load_shelters
from weatherwise.weather import ATTRIBUTION
from weatherwise.weather.area_weather import build_area_weather, fetch_raw_inputs

ROOT = Path(__file__).resolve().parents[2]
# Where downloads and cached forecasts live. On AWS Lambda only /tmp is writable.
CACHE_ROOT = Path(os.environ.get("WEATHERWISE_CACHE_DIR", ROOT / "cache"))
# Places worked out before deploy (decades of history each; see scripts/seed_cache.py).
SEED_ROOT = ROOT / "data" / "cache_seed"


def default_cache(cache_root: Path = CACHE_ROOT) -> Cache:
    """This container's disk, then (WEATHERWISE_CACHE_BUCKET) the bucket shared with the agents
    on AgentCore, then the shipped seed. A new place's 30-year history costs about 3,000 of the
    free weather tier's 10,000 daily calls, so it is fetched once and kept."""
    layers: list = [FileCache(cache_root / "store")]
    if bucket := os.environ.get("WEATHERWISE_CACHE_BUCKET"):
        layers.append(S3Cache(bucket))
    if SEED_ROOT.exists():
        layers.append(FileCache(SEED_ROOT, read_only=True))
    return LayeredCache(layers) if len(layers) > 1 else layers[0]
# The coastline file (10 MB, downloaded once); a container can ship it read-only elsewhere.
GEODATA_ROOT = Path(os.environ.get("WEATHERWISE_GEODATA_DIR", CACHE_ROOT / "geodata"))
MAX_BACKTEST_DAYS = 62


def detection_dict(d: HazardDetection) -> dict:
    out = asdict(d)
    out["hazard"] = d.hazard.value
    out["first_day"], out["last_day"] = d.first_day.isoformat(), d.last_day.isoformat()
    return out


def not_covered(e: UnsupportedCountry) -> dict:
    """The answer for a place outside every country we have rules for: honest, never a guess.
    No helpline numbers: ours are for the countries we cover, not this one."""
    return {
        "covered": False,
        "country_code": e.country_code,
        "covered_countries": supported_countries(),
        "instruction": "Tell the person this place is not covered yet. Do not guess warnings, "
                       "shelters or helplines; suggest their local emergency number.",
        "rules_version": rules_version(),
    }


@dataclass
class ClimateRiskServices:
    resolver: PlaceResolver
    geocoders: list[Geocoder]
    health: HealthFacilityFinder | None
    today_fn: object = field(default=None)  # callable(timezone) -> date; injected for tests
    official: SachetAlerts | None = None    # official warnings; None = not connected (tests)

    @classmethod
    def default(cls, cache_root: Path = CACHE_ROOT) -> "ClimateRiskServices":
        cache = default_cache(cache_root)
        nominatim = NominatimGeocoder()
        return cls(
            resolver=PlaceResolver(nominatim, Coastline(GEODATA_ROOT / "ne_10m_coastline.geojson"), cache),
            geocoders=[OpenMeteoGeocoder(), nominatim],
            health=OsmHealthFacilities(cache),
            official=SachetAlerts(cache),
        )

    def _today(self, timezone: str) -> date:
        if self.today_fn:
            return self.today_fn(timezone)
        return datetime.now(ZoneInfo(timezone)).date()

    def _place(self, lat: float, lon: float, name: str | None = None) -> tuple[PlaceContext, dict, date]:
        today = self._today("UTC")
        place = self.resolver.resolve(lat, lon, name=name, today=today)
        rules = load_rules(place.country)
        return place, rules, self._today(place.timezone)

    # ---- tools ---------------------------------------------------------------------
    def find_place(self, name: str, country_code: str = "in", language: str = "en") -> dict:
        """Cached 30 days per name and language: the public geocoders ask callers to cache repeat
        lookups."""
        def search() -> list[dict]:
            return [{"label": c.label, "lat": c.lat, "lon": c.lon, "source": c.source}
                    for c in search_place(name, country_code, self.geocoders, language=language)[:8]]

        key = f"{country_code.lower()}:{name.strip().lower()}" + ("" if language == "en" else f":{language}")
        candidates = cached(self.resolver.cache, "geocode", key, search)
        return {
            "query": name,
            "candidates": candidates,
            "instruction": "Always confirm the place with the person before using it.",
            "rules_version": rules_version(),
        }

    def message_policy(self, country_code: str = "in") -> dict:
        return message_policy(country_for(country_code))

    def resolve_place(self, lat: float, lon: float) -> dict:
        try:
            place, _, _ = self._place(lat, lon)
        except UnsupportedCountry as e:
            return not_covered(e)
        return {**place.summary(), "covered": True, "rules_version": rules_version()}

    def hazard_outlook(self, lat: float, lon: float, name: str | None = None) -> dict:
        try:
            place, rules, today = self._place(lat, lon, name)
        except UnsupportedCountry as e:
            return not_covered(e)
        weather = self.resolver.weather(place.timezone)
        raw = fetch_raw_inputs(place, weather, rules, today)
        area_weather = build_area_weather(raw, today, rules)
        official = self._official(lat, lon, rules)
        # An official red flood/rain/cyclone alert starts the flood guide in urgent mode, orange in prepare.
        result = scan_area(place.as_area(), area_weather, today, rules,
                           official_alert=most_serious(official["alerts"], flood_only=True))
        return {
            "place": {"name": place.name, "district": place.admin.district, "state": place.admin.state,
                      "terrain": place.terrain.value, "large_river_nearby": place.river.is_river_area,
                      "forecast_cell": place.cell.key},
            "covered": True,
            "issue_date": today.isoformat(),
            "detections": [detection_dict(d) for d in result.detections],
            "flood_guide": {"mode": result.flood_guide.mode, "reasons": result.flood_guide.reasons},
            "data_missing": [h.value for h in result.data_missing],
            "days": daily_outlook(area_weather, result.detections,
                                 rainy_day_mm=rules["dry_spell"]["dry_day_max_mm"]),
            "forecast_correction": area_weather.correction,
            "official": official,
            "flood_level_m3s": place.river.flood_level_m3s if place.river.is_river_area else None,
            "rules_note": "Numbers come from forecasts, never from AI. 'ours' rules are labelled; "
                          "official warnings (IMD) always win.",
            "rules_version": rules_version(),
            "attribution": ATTRIBUTION,
        }

    def _official(self, lat: float, lon: float, rules: dict) -> dict:
        provider = rules.get("official_alerts", {}).get("provider")
        if provider == "sachet" and self.official is not None:
            return self.official.for_point(lat, lon)
        return {"status": "not_connected", "alerts": [], "source": None}

    def official_alerts(self, lat: float, lon: float) -> dict:
        """Needs only the country (to pick the official source), not our forecast: official
        warnings must still show when the weather service is down or rate-limited."""
        try:
            country = country_for(self.resolver.admin(lat, lon).country_code)
        except UnsupportedCountry as e:
            return not_covered(e)
        except Exception:  # place lookup down: we cannot tell which official source applies
            return {"status": "unavailable", "alerts": [], "source": None, "covered": True,
                    "rules_version": rules_version()}
        return {**self._official(lat, lon, load_rules(country)), "covered": True, "rules_version": rules_version()}

    def find_shelters(self, lat: float, lon: float, hazard: str) -> dict:
        try:
            place, rules, today = self._place(lat, lon)
        except UnsupportedCountry as e:
            return not_covered(e)
        cfg = rules.get("shelters", {})
        result = find_shelters(
            lat, lon, hazard, load_shelters(place.country), rules["helplines"], self.health, today,
            search_km=cfg.get("search_km", 20.0), max_results=cfg.get("max_results", 3),
        )
        return {**result, "covered": True, "rules_version": rules_version()}

    def backtest(self, lat: float, lon: float, first_day: str, last_day: str,
                 name: str | None = None) -> dict:
        first, last = date.fromisoformat(first_day), date.fromisoformat(last_day)
        if last < first or (last - first).days >= MAX_BACKTEST_DAYS:
            raise ValueError(f"date range must be 1 to {MAX_BACKTEST_DAYS} days")
        place, rules, today = self._place(lat, lon, name)
        if last > today - timedelta(days=6):
            raise ValueError("last_day must be at least 6 days ago (observations lag ~5 days)")
        weather = self.resolver.weather(place.timezone)
        bt = backtest_place(place, first, last, weather, rules)
        return {
            "place": {"name": place.name, "district": place.admin.district, "state": place.admin.state},
            "mode": bt.mode,
            "flood_level_m3s": bt.flood_level_m3s,
            "unusual_rain_mm": bt.unusual_rain_mm,
            "verification": verify(bt),
            "timeline": [
                {
                    "day": d.day.isoformat(),
                    "would_have_sent": sorted({f"{w['hazard']}:{w['severity']}" for w in d.warnings}),
                    "flood_guide": d.flood_guide_mode,
                    "flood_guide_reasons": d.flood_guide_reasons,
                    "forecast_correction": d.correction,
                    "what_happened": d.observed_events,
                    "observed": d.observed,
                }
                for d in bt.days
            ],
            "notes": bt.notes,
            "attribution": ATTRIBUTION,
        }

    def cap_alerts(self, lat: float, lon: float, status: str = "Exercise") -> dict:
        outlook = self.hazard_outlook(lat, lon)
        if not outlook["covered"]:
            return outlook
        place, rules, _ = self._place(lat, lon)
        alerts = []
        for d in outlook["detections"]:
            det = HazardDetection(**{**d, "hazard": Hazard(d["hazard"]),
                                     "first_day": date.fromisoformat(d["first_day"]),
                                     "last_day": date.fromisoformat(d["last_day"])})
            alerts.append(detection_to_cap(
                det, area_desc=f"{place.name}, {place.admin.district}, {place.admin.state}",
                lat=lat, lon=lon, timezone=place.timezone,
                headline=f"{det.hazard.value.replace('_', ' ').title()} expected near {place.name}",
                instruction=f"Follow official IMD advice. Call {rules['helplines']['disaster']} for help.",
                status=status))
        return {"count": len(alerts), "alerts": alerts}
