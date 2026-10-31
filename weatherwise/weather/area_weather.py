"""Builds AreaWeather for any resolved place, from cell-cached forecasts and baselines."""

from datetime import date

from weatherwise.places.grid import grid_cell
from weatherwise.places.resolve import PlaceContext
from weatherwise.risk.area_scan import AreaWeather
from weatherwise.weather import open_meteo as om
from weatherwise.weather.service import WeatherService


def fetch_raw_inputs(place: PlaceContext, weather: WeatherService, rules: dict) -> dict:
    """Every live input for one place, as raw JSON (savable as a test snapshot)."""
    raw = {
        "ensemble": weather.ensemble(place.cell),
        "recent": weather.recent(place.cell),
        "normal_tmax": weather.normal_tmax(place.cell),
        "heat_climate": weather.heat_climate(place.cell, rules),
    }
    if place.river.is_river_area:
        raw["river"] = weather.river_forecast(place.river.river_lat, place.river.river_lon)
        raw["flood_level_m3s"] = place.river.flood_level_m3s
        raw["upstream"] = {
            p.name: weather.ensemble(grid_cell(p.lat, p.lon)) for p in place.river.upstream_rain_points
        }
    return raw


def build_area_weather(raw: dict, today: date, rules: dict) -> AreaWeather:
    past_dry_days, soil_moisture = om.parse_recent_conditions(
        raw["recent"], today, rules["dry_spell"]["dry_day_max_mm"]
    )
    return AreaWeather(
        tmax=om.parse_ensemble(raw["ensemble"], "temperature_2m_max"),
        feels_like_tmax=om.parse_ensemble(raw["ensemble"], "apparent_temperature_max"),
        rainfall=om.parse_ensemble(raw["ensemble"], "precipitation_sum"),
        normal_tmax=raw["normal_tmax"],
        past_dry_days=past_dry_days,
        soil_moisture=soil_moisture,
        river_discharge=om.parse_ensemble(raw["river"], "river_discharge") if "river" in raw else None,
        flood_level_m3s=raw.get("flood_level_m3s"),
        upstream_rainfall={
            name: om.parse_ensemble(r, "precipitation_sum") for name, r in raw.get("upstream", {}).items()
        },
        mean_temp=om.parse_ensemble(raw["ensemble"], "temperature_2m_mean")
        if "temperature_2m_mean" in raw["ensemble"]["daily"] else None,
        past_30_day_means=om.parse_past_daily_means(raw["recent"], today)
        if "temperature_2m_mean" in raw["recent"]["daily"] else [],
        heat_climate=raw.get("heat_climate"),
    )
