"""Terrain from elevation and distance to the coast, never typed by hand (plan §8.9).

Cut-offs (coast within N km, hills above M metres) are country config, because each
weather service defines its station types differently.
"""

import json
import urllib.request
from pathlib import Path

from weatherwise.places.geocoding import distance_km
from weatherwise.risk.models import TerrainZone

# Pinned to a release so every deployment derives the same terrain.
COASTLINE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
    "ne_10m_coastline.geojson"
)


class Coastline:
    """Natural Earth 1:10m coastline (public domain), downloaded once and kept locally."""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self._points: list[tuple[float, float]] | None = None

    def _load(self) -> list[tuple[float, float]]:
        if self._points is None:
            if not self.cache_file.exists():
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(COASTLINE_URL, timeout=120) as resp:
                    self.cache_file.write_bytes(resp.read())
            data = json.loads(self.cache_file.read_text())
            points = []
            for feature in data["features"]:
                geometry = feature["geometry"]
                lines = (
                    [geometry["coordinates"]]
                    if geometry["type"] == "LineString"
                    else geometry["coordinates"]
                )
                for line in lines:
                    points.extend((lat, lon) for lon, lat in line)
            self._points = points
        return self._points

    def distance_km(self, lat: float, lon: float, search_deg: float = 3.0) -> float | None:
        """Distance to the nearest coastline vertex; None if no coast within search_deg."""
        nearby = [
            (plat, plon)
            for plat, plon in self._load()
            if abs(plat - lat) <= search_deg and abs(plon - lon) <= search_deg
        ]
        if not nearby:
            return None
        return round(min(distance_km(lat, lon, plat, plon) for plat, plon in nearby), 1)


def classify_terrain(elevation_m: float, coast_km: float | None, rules: dict) -> TerrainZone:
    """rules: the country's [terrain] config (coast_max_km, hills_min_elevation_m)."""
    if coast_km is not None and coast_km <= rules["coast_max_km"]:
        return TerrainZone.COAST
    if elevation_m >= rules["hills_min_elevation_m"]:
        return TerrainZone.HILLS
    return TerrainZone.PLAINS
