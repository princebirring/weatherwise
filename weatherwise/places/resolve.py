"""resolve_place: any coordinate -> everything the system needs to know about it (plan §8.9)."""

from dataclasses import asdict, dataclass, field
from datetime import date

from weatherwise.cache import Cache, cached
from weatherwise.places.geocoding import AdminArea, ReverseGeocoder, distance_km
from weatherwise.places.grid import RIVER_GRID_DEG, GridCell, grid_cell
from weatherwise.places.terrain import Coastline, classify_terrain
from weatherwise.risk.models import Area, RainPoint, TerrainZone
from weatherwise.rules import country_for, load_river_catchments, load_rules
from weatherwise.weather import open_meteo as om
from weatherwise.weather.service import WeatherService


@dataclass(frozen=True)
class RiverExposure:
    flood_level_m3s: float              # 1-in-N-year flow of the nearest real river
    is_river_area: bool                 # big enough to be a real river, not a stream
    river_lat: float                    # the river cell every river check uses
    river_lon: float
    upstream_rain_points: tuple[RainPoint, ...] = ()
    upstream_source: str | None = None  # where the upstream points came from (pilot data)


@dataclass(frozen=True)
class PlaceContext:
    lat: float
    lon: float
    name: str
    admin: AdminArea
    country: str                   # rules key, e.g. "in" (rules/countries/in.toml)
    timezone: str                  # from the coordinates, e.g. "Asia/Kolkata"
    cell: GridCell
    elevation_m: float
    coast_km: float | None
    terrain: TerrainZone
    river: RiverExposure
    derived_from: dict = field(default_factory=dict)  # which source gave each fact

    def as_area(self) -> Area:
        """The Risk Engine's view of this place."""
        return Area(
            id=f"pt:{self.lat:.3f}:{self.lon:.3f}",
            name=self.name,
            district=self.admin.district or "",
            terrain=self.terrain,
            lat=self.lat,
            lon=self.lon,
        )

    def summary(self) -> dict:
        d = asdict(self)
        d["terrain"] = self.terrain.value
        d["cell"] = self.cell.key
        return d

    @classmethod
    def from_summary(cls, d: dict) -> "PlaceContext":
        """Rebuild from summary() output (used to replay saved backtests offline)."""
        size, lat, lon = d["cell"].split(":")
        r = d["river"]
        return cls(
            lat=d["lat"], lon=d["lon"], name=d["name"], admin=AdminArea(**d["admin"]),
            country=d["country"], timezone=d["timezone"], cell=GridCell(float(lat), float(lon), float(size)),
            elevation_m=d["elevation_m"], coast_km=d["coast_km"], terrain=TerrainZone(d["terrain"]),
            river=RiverExposure(
                r["flood_level_m3s"], r["is_river_area"], r["river_lat"], r["river_lon"],
                tuple(RainPoint(**p) for p in r["upstream_rain_points"]), r["upstream_source"]),
            derived_from=d.get("derived_from", {}),
        )


def _upstream_points(lat: float, lon: float, country: str) -> tuple[tuple[RainPoint, ...], str | None]:
    for c in load_river_catchments(country):
        if distance_km(lat, lon, c["outlet_lat"], c["outlet_lon"]) <= c["applies_within_km"]:
            return c["upstream_rain_points"], f"{c['name']} ({c['status']})"
    return (), None


@dataclass
class PlaceResolver:
    reverse_geocoder: ReverseGeocoder
    coastline: Coastline
    cache: Cache
    weather_for_tz: dict = field(default_factory=dict)
    fetch_timezone: object = om.fetch_timezone  # injectable for tests

    def weather(self, timezone: str) -> WeatherService:
        if timezone not in self.weather_for_tz:
            self.weather_for_tz[timezone] = WeatherService(self.cache, timezone)
        return self.weather_for_tz[timezone]

    def timezone(self, lat: float, lon: float) -> str:
        return cached(self.cache, "admin", f"tz:{lat:.2f}:{lon:.2f}", lambda: self.fetch_timezone(lat, lon))

    def admin(self, lat: float, lon: float) -> AdminArea:
        key = f"{lat:.2f}:{lon:.2f}"
        value = cached(self.cache, "admin", key,
                       lambda: asdict(self.reverse_geocoder.reverse(lat, lon)))
        return AdminArea(**value)

    @staticmethod
    def _nearest_river(weather: WeatherService, lat: float, lon: float, rules: dict,
                       today: date) -> tuple[float, float, float]:
        """The nearest real river (within ~5 km) and its flood level."""
        last_year = today.year - 1
        cell = weather.nearest_river_cell(
            lat, lon, rules["river_exposure"]["screen_years"], last_year
        )
        try:
            level = weather.flood_level(cell.lat, cell.lon, rules, last_year)
        except (ValueError, KeyError, TypeError):  # no river history (e.g. open sea)
            level = 0.0
        return cell.lat, cell.lon, level

    def resolve(self, lat: float, lon: float, name: str | None = None,
                today: date | None = None) -> PlaceContext:
        today = today or date.today()
        admin = self.admin(lat, lon)
        country = country_for(admin.country_code)
        rules = load_rules(country)
        timezone = self.timezone(lat, lon)
        weather = self.weather(timezone)

        elevation = weather.elevation(lat, lon)
        coast_km = self.coastline.distance_km(lat, lon)
        terrain = classify_terrain(elevation, coast_km, rules["terrain"])

        river_lat, river_lon, flood_level = self._nearest_river(weather, lat, lon, rules, today)
        is_river = flood_level >= rules["river_exposure"]["min_flood_flow_m3s"]
        upstream, source = _upstream_points(lat, lon, country) if is_river else ((), None)

        return PlaceContext(
            lat=lat,
            lon=lon,
            name=name or admin.district or f"{lat:.3f}, {lon:.3f}",
            admin=admin,
            country=country,
            timezone=timezone,
            cell=grid_cell(lat, lon),
            elevation_m=elevation,
            coast_km=coast_km,
            terrain=terrain,
            river=RiverExposure(flood_level, is_river, river_lat, river_lon, upstream, source),
            derived_from={
                "admin": "reverse geocoding (OpenStreetMap Nominatim)",
                "elevation": "Open-Meteo elevation API (Copernicus DEM)",
                "coast": "Natural Earth 1:10m coastline",
                "river": f"GloFAS river history, {RIVER_GRID_DEG} deg cell, "
                         f"1-in-{rules['river_flood']['flood_level_return_period_years']}-year flow",
            },
        )
