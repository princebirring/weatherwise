"""Finds the right place for the hazard near any point. Plain code, no AI:
it cannot invent a shelter.

Rules:
- heat -> cooling centers; flood, cyclone, other -> shelters;
- only shelters that pass the acceptance fields in data/SHELTERS_README.md and are not past their re-check date;
- heat with no cooling center nearby -> say so honestly + nearest health facilities
  (OpenStreetMap, labelled unverified);
- floods: never a map route (maps do not know which roads are underwater);
- always the disaster helpline, so people can confirm the place is open.
"""

import csv
import json
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from weatherwise.cache import Cache
from weatherwise.https import urlopen
from weatherwise.places.geocoding import USER_AGENT, distance_km
from weatherwise.places.grid import grid_cell
from weatherwise.rules import DATA_ROOT

REQUIRED_FIELDS = ("name", "type", "lat", "lon", "hazards", "source", "checked_on", "recheck_due")
PLACE_TYPE_FOR_HAZARD = {"heat": "cooling_center", "flood": "shelter", "cyclone": "shelter",
                         "other": "shelter"}
FLOOD_SAFETY_LINE = ("Use the high road. Never walk or drive through flowing water. "
                     "Move away from rivers and away from hill slopes.")


@dataclass(frozen=True)
class Shelter:
    name: str
    type: str          # cooling_center | shelter
    lat: float
    lon: float
    hazards: tuple[str, ...]
    district: str
    source: str
    contact: str
    checked_on: date
    recheck_due: date


class HealthFacilityFinder(Protocol):
    def near(self, lat: float, lon: float, radius_km: float) -> list[dict]: ...


class OsmHealthFacilities:
    """Hospitals, clinics and health centres from OpenStreetMap (ODbL), via public Overpass
    mirrors (tried in order). Production: Amazon Location or a self-hosted Overpass.

    The public mirrors can take a minute or fail. A person asking for shelter must not wait
    for them: near() waits at most wait_seconds, and if the lookup is still running it raises
    TimeoutError while the download carries on in the background and fills the cache for the
    next request in that cell. Later askers never wait for a download someone else started,
    and after a failure the mirrors are left alone for RETRY_AFTER_SECONDS."""

    MIRRORS = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    )
    CELL_RADIUS_KM = 18.0  # half the diagonal of a 0.25 deg cell, so the cell is covered
    WAIT_SECONDS = 6.0
    MIRROR_TIMEOUT_SECONDS = 25
    RETRY_AFTER_SECONDS = 600

    def __init__(self, cache: Cache, wait_seconds: float = WAIT_SECONDS):
        self.cache = cache
        self.wait_seconds = wait_seconds
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="osm-health")
        self._running: dict[str, Future] = {}
        self._failed_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def near(self, lat: float, lon: float, radius_km: float) -> list[dict]:
        """Facilities within radius_km. Fetched once per forecast grid cell (shared by ~150
        villages, cached 30 days, pre-loadable by the daily job), then filtered by distance."""
        cell = grid_cell(lat, lon)
        everything = self.for_cell(cell, radius_km)
        return [f for f in everything if distance_km(lat, lon, f["lat"], f["lon"]) <= radius_km]

    def for_cell(self, cell, radius_km: float) -> list[dict]:
        key = f"{cell.key}:{radius_km}"
        hit = self.cache.get("health_facilities", key)
        if hit is not None:
            return hit
        with self._lock:  # one download per cell, however many people ask at once
            if time.monotonic() - self._failed_at.get(key, -self.RETRY_AFTER_SECONDS) < self.RETRY_AFTER_SECONDS:
                raise TimeoutError("health facility mirrors failed recently")
            if key in self._running:
                raise TimeoutError("health facilities still downloading")
            job = self._running[key] = self._pool.submit(self._download_and_store, key, cell, radius_km)
        return job.result(timeout=self.wait_seconds)  # TimeoutError: still downloading

    def _download_and_store(self, key: str, cell, radius_km: float) -> list[dict]:
        try:
            facilities = self.download(cell.lat, cell.lon, int((radius_km + self.CELL_RADIUS_KM) * 1000))
            self.cache.put("health_facilities", key, facilities)
            return facilities
        except Exception:
            with self._lock:
                self._failed_at[key] = time.monotonic()
            raise
        finally:
            with self._lock:
                self._running.pop(key, None)

    def download(self, lat: float, lon: float, radius_m: int) -> list[dict]:
        query = (f'[out:json][timeout:{self.MIRROR_TIMEOUT_SECONDS}];'
                 f'node["amenity"~"^(hospital|clinic)$"](around:{radius_m},{lat},{lon});out 200;')
        data = urllib.parse.urlencode({"data": query}).encode()
        last_error: Exception | None = None
        for url in self.MIRRORS:
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
                with urlopen(req, timeout=self.MIRROR_TIMEOUT_SECONDS) as resp:
                    elements = json.load(resp)["elements"]
                break
            except Exception as e:
                last_error = e
        else:
            raise ConnectionError(f"all Overpass mirrors failed: {last_error}")
        return [
            {"name": e["tags"].get("name", "Health facility"), "lat": e["lat"], "lon": e["lon"],
             "kind": e["tags"].get("healthcare") or e["tags"].get("amenity")}
            for e in elements if "lat" in e
        ]


def load_shelters(country: str, root: Path = DATA_ROOT) -> list[Shelter]:
    """Verified shelters for a country (data/shelters_<country>.csv). Rows missing a required
    acceptance field are rejected."""
    path = root / f"shelters_{country}.csv"
    if not path.exists():
        return []
    shelters = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if any(not row.get(k) for k in REQUIRED_FIELDS):
                continue
            shelters.append(Shelter(
                name=row["name"], type=row["type"], lat=float(row["lat"]), lon=float(row["lon"]),
                hazards=tuple(h.strip() for h in row["hazards"].split(";")),
                district=row.get("district", ""), source=row["source"],
                contact=row.get("contact", ""),
                checked_on=date.fromisoformat(row["checked_on"]),
                recheck_due=date.fromisoformat(row["recheck_due"]),
            ))
    return shelters


def find_shelters(
    lat: float,
    lon: float,
    hazard: str,
    shelters: list[Shelter],
    helplines: dict,
    health: HealthFacilityFinder | None,
    today: date,
    search_km: float = 20.0,
    max_results: int = 3,
) -> dict:
    place_type = PLACE_TYPE_FOR_HAZARD.get(hazard, "shelter")
    fresh = [s for s in shelters if s.recheck_due >= today]
    stale_nearby = [s for s in shelters if s.recheck_due < today
                    and distance_km(lat, lon, s.lat, s.lon) <= search_km]
    candidates = sorted(
        ((distance_km(lat, lon, s.lat, s.lon), s) for s in fresh
         if s.type == place_type and (hazard in s.hazards or hazard == "other")),
        key=lambda x: x[0],
    )
    nearby = [(km, s) for km, s in candidates if km <= search_km][:max_results]

    result = {
        "hazard": hazard,
        "place_type": place_type,
        "places": [
            {"name": s.name, "km": round(km, 1), "contact": s.contact, "source": s.source,
             "checked_on": s.checked_on.isoformat(), "verified": True,
             "directions_link": None if hazard == "flood" else
             f"https://www.openstreetmap.org/directions?route={lat}%2C{lon}%3B{s.lat}%2C{s.lon}"}
            for km, s in nearby
        ],
        "helpline": {"disaster": helplines.get("disaster"), "ambulance": helplines.get("ambulance"),
                     "emergency": helplines.get("emergency")},
        "notes": [],
        # The same facts as the notes, as data, so screens can say them in any language.
        "search_km": search_km,
        "stale_nearby": len(stale_nearby),
        "health_status": "not_needed",
    }
    if hazard == "flood":
        result["notes"].append(FLOOD_SAFETY_LINE)
        result["notes"].append("No map route: maps do not know which roads are underwater.")
    if stale_nearby:
        result["notes"].append(
            f"{len(stale_nearby)} nearby place(s) not shown: overdue for re-checking.")
    if not nearby:
        result["notes"].append(
            f"No verified {place_type.replace('_', ' ')} within {search_km:.0f} km. "
            f"Call {helplines.get('disaster')} to find the nearest open one.")
        if hazard == "heat" and health is not None:
            try:
                facilities = sorted(
                    ((distance_km(lat, lon, h["lat"], h["lon"]), h) for h in health.near(lat, lon, search_km)),
                    key=lambda x: x[0])[:max_results]
            except Exception:
                facilities = []
                result["health_status"] = "unavailable"
                result["notes"].append(
                    f"Nearby health facilities could not be loaded right now. "
                    f"For an ambulance call {helplines.get('ambulance')}.")
            if facilities:
                result["health_status"] = "ok"
            result["health_facilities"] = [
                {"name": h["name"], "kind": h["kind"], "km": round(km, 1),
                 "source": "OpenStreetMap (unverified)"} for km, h in facilities]
    result["confirm_line"] = f"Call {helplines.get('disaster')} to confirm the place is open."
    return result
