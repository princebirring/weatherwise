"""Village names to coordinates, and coordinates to admin area (plan §3, §8.9).

Two open geocoders are merged because each knows villages the other misses:
Open-Meteo (GeoNames) and Nominatim (OpenStreetMap). In production, Amazon Location
implements the same Geocoder interface. Results are always confirmed back to the user.
"""

import json
import math
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from weatherwise.https import urlopen

USER_AGENT = "weatherwise/0.1 (AWS Strands hackathon; open source)"


@dataclass(frozen=True)
class AdminArea:
    country_code: str  # ISO 3166-1 alpha-2, lower case: "in", "ke"
    state: str | None
    district: str | None


@dataclass(frozen=True)
class PlaceCandidate:
    name: str
    lat: float
    lon: float
    admin: AdminArea
    source: str

    @property
    def label(self) -> str:
        parts = [self.name, self.admin.district, self.admin.state]
        return ", ".join(p for p in parts if p)


class Geocoder(Protocol):
    def search(self, name: str, country_code: str, language: str = "en") -> list[PlaceCandidate]: ...


class ReverseGeocoder(Protocol):
    def reverse(self, lat: float, lon: float) -> AdminArea: ...


def _get_json(url: str, params: dict, timeout: float = 20) -> object:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as resp:
        return json.load(resp)


def _clean_district(name: str | None) -> str | None:
    if not name:
        return None
    for suffix in (" District", " district", " जिल्हा", " जिला"):  # English, Marathi, Hindi
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


class OpenMeteoGeocoder:
    URL = "https://geocoding-api.open-meteo.com/v1/search"

    def search(self, name: str, country_code: str, language: str = "en") -> list[PlaceCandidate]:
        data = _get_json(self.URL, {"name": name, "count": 10, "countryCode": country_code.upper(),
                                    "language": language})
        return [
            PlaceCandidate(
                name=r["name"],
                lat=r["latitude"],
                lon=r["longitude"],
                admin=AdminArea(country_code.lower(), r.get("admin1"), _clean_district(r.get("admin2"))),
                source="open-meteo",
            )
            for r in data.get("results", [])
        ]


class NominatimGeocoder:
    """OpenStreetMap Nominatim. Public-server policy: max 1 request/second, named user agent."""

    URL = "https://nominatim.openstreetmap.org"
    _lock = threading.Lock()
    _last_call = 0.0

    def _throttled(self, path: str, params: dict, language: str = "en") -> object:
        with self._lock:
            wait = 1.0 - (time.monotonic() - NominatimGeocoder._last_call)
            if wait > 0:
                time.sleep(wait)
            NominatimGeocoder._last_call = time.monotonic()
        # Names in the person's language where OpenStreetMap has them, else English.
        accept = language if language == "en" else f"{language},en"
        return _get_json(f"{self.URL}/{path}", {**params, "format": "jsonv2", "accept-language": accept})

    @staticmethod
    def _admin(address: dict) -> AdminArea:
        district = address.get("state_district") or address.get("county")
        return AdminArea(address.get("country_code", ""), address.get("state"), _clean_district(district))

    def search(self, name: str, country_code: str, language: str = "en") -> list[PlaceCandidate]:
        results = self._throttled(
            "search", {"q": name, "countrycodes": country_code, "addressdetails": 1, "limit": 10}, language
        )
        return [
            PlaceCandidate(
                name=r.get("name") or name,
                lat=float(r["lat"]),
                lon=float(r["lon"]),
                admin=self._admin(r.get("address", {})),
                source="openstreetmap",
            )
            for r in results
        ]

    def reverse(self, lat: float, lon: float) -> AdminArea:
        result = self._throttled("reverse", {"lat": lat, "lon": lon, "zoom": 10})
        return self._admin(result.get("address", {}))


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def search_place(
    name: str, country_code: str, geocoders: list[Geocoder], same_place_km: float = 2.0, language: str = "en"
) -> list[PlaceCandidate]:
    """Candidates from all geocoders, with duplicates (within same_place_km) merged. Names come in
    `language` (e.g. "mr") where the geocoder has them, else in English.

    A geocoder that fails is skipped, so one outage never blocks sign-up.
    """
    merged: list[PlaceCandidate] = []
    for geocoder in geocoders:
        try:
            found = geocoder.search(name, country_code, language)
        except Exception:  # noqa: S112 - one geocoder down must never block finding a village
            continue
        for c in found:
            if not any(distance_km(c.lat, c.lon, m.lat, m.lon) < same_place_km for m in merged):
                merged.append(c)
    return merged
