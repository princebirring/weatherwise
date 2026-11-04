"""WeatherService: every weather fetch, cached by grid cell.

Villages in the same 0.25° cell share forecasts and normals; places in the same
0.05° river cell share river data. This is what makes cost grow with cells, not people.
Swap the fetch module for another provider without touching callers.
"""

from datetime import date

from weatherwise.cache import Cache, cached
from weatherwise.places.grid import GridCell, river_cell
from weatherwise.weather import open_meteo as om


class WeatherService:
    def __init__(self, cache: Cache, timezone: str, fetch=om):
        self.cache = cache
        self.tz = timezone
        self.fetch = fetch

    # ---- live --------------------------------------------------------------------
    def ensemble(self, cell: GridCell) -> dict:
        return cached(self.cache, "forecast", f"{cell.key}:{self.tz}",
                      lambda: self.fetch.fetch_ensemble_forecast(cell, self.tz))

    def recent(self, cell: GridCell) -> dict:
        return cached(self.cache, "recent", f"{cell.key}:{self.tz}",
                      lambda: self.fetch.fetch_recent_conditions(cell, self.tz))

    def river_forecast(self, lat: float, lon: float) -> dict:
        cell = river_cell(lat, lon)
        return cached(self.cache, "river_forecast", cell.key,
                      lambda: self.fetch.fetch_river_discharge_forecast(cell))

    # ---- baselines ----------------------------------------------------------------
    def normal_tmax(self, cell: GridCell) -> dict[str, float]:
        return cached(self.cache, "normals", f"{cell.key}:{self.tz}",
                      lambda: om.parse_normal_tmax(self.fetch.fetch_historical_tmax(cell, self.tz)))

    def heat_climate(self, cell: GridCell, rules: dict) -> dict:
        """This cell's Excess Heat Factor baseline (95th-percentile mean temp, severe EHF)."""
        from weatherwise.risk.heat_wave import heat_climate  # pure function

        eh = rules["excess_heat"]
        key = f"{cell.key}:{self.tz}:ehf:{eh['reference_first_year']}-{eh['reference_last_year']}"

        def compute() -> dict:
            raw = self.fetch.fetch_historical_daily(
                cell, self.tz, "temperature_2m_mean", eh["reference_first_year"], eh["reference_last_year"])
            means = [v for v in raw["daily"]["temperature_2m_mean"] if v is not None]
            return heat_climate(means, eh["heat_percentile"], eh["severe_percentile"])

        return cached(self.cache, "normals", key, compute)

    def rain_climate(self, cell: GridCell, rules: dict) -> dict:
        """This cell's unusual-rain line (a high percentile of its own daily rain)."""
        from weatherwise.risk.heavy_rain import rain_climate  # pure function

        ur = rules["unusual_rain"]
        key = (f"{cell.key}:{self.tz}:rain:{ur['reference_first_year']}-{ur['reference_last_year']}"
               f":p{ur['percentile']}:min{ur['min_mm']}")

        def compute() -> dict:
            raw = self.fetch.fetch_historical_daily(
                cell, self.tz, "precipitation_sum", ur["reference_first_year"], ur["reference_last_year"])
            rain = [v for v in raw["daily"]["precipitation_sum"] if v is not None]
            return rain_climate(rain, ur["percentile"], ur["min_mm"])

        return cached(self.cache, "normals", key, compute)

    def recent_errors(self, cell: GridCell, today: date, rules: dict) -> dict:
        """The live forecast model's day-ahead forecasts for the correction's training days,
        and what happened on them: the raw inputs of the forecast correction."""
        from weatherwise.weather.correction import training_window  # pure function

        first, last = training_window(today, rules["forecast_correction"])
        return cached(self.cache, "correction", f"{cell.key}:{self.tz}:{first}:{last}", lambda: {
            "issued": self.fetch.fetch_heat_as_issued(cell, first, last, self.tz,
                                                      models=(om.ENSEMBLE_MODEL,), max_previous_day=1),
            "observed": self.fetch.fetch_observed_daily(cell, first, last, self.tz),
        })

    def flood_level(self, lat: float, lon: float, rules: dict, last_year: int) -> float:
        """1-in-N-year flow from river history up to last_year (inclusive)."""
        flood = rules["river_flood"]
        cell = river_cell(lat, lon)
        years = flood["flood_level_return_period_years"]
        key = f"{cell.key}:{years}y:{flood['history_first_year']}-{last_year}"

        def compute() -> float:
            history = self.fetch.fetch_historical_river_discharge(
                cell, flood["history_first_year"], last_year
            )
            return om.parse_flood_level(history, years)

        return cached(self.cache, "flood_level", key, compute)

    def nearest_river_cell(self, lat: float, lon: float, screen_years: int, last_year: int) -> GridCell:
        """Which of the point's river cell and its 8 neighbours carries the most water.

        Cheap screen: one request for all 9 cells over a few recent years. Rivers are
        narrow, so the point's own cell often misses the river beside it.
        """
        from weatherwise.places.grid import neighbour_ring  # local: grid imports nothing from here

        home = river_cell(lat, lon)
        cells = [home, *neighbour_ring(home)]
        key = f"{home.key}:screen:{last_year - screen_years + 1}-{last_year}"

        def compute() -> list[float]:
            responses = self.fetch.fetch_river_discharge_many(
                cells, date(last_year - screen_years + 1, 1, 1), date(last_year, 12, 31),
                om.RIVER_REANALYSIS_MODEL,
            )
            return [max((v for v in r["daily"]["river_discharge"] if v is not None), default=0.0)
                    for r in responses]

        peaks = cached(self.cache, "flood_level", key, compute)
        return cells[max(range(len(cells)), key=lambda i: peaks[i])]

    def elevation(self, lat: float, lon: float) -> float:
        return cached(self.cache, "elevation", f"{lat:.3f}:{lon:.3f}",
                      lambda: self.fetch.fetch_elevation(lat, lon))

    # ---- archives (backtests) -------------------------------------------------------
    def _archive(self, name: str, place, first: date, last: date, call) -> dict:
        key = f"{name}:{place.lat:.3f}:{place.lon:.3f}:{first}:{last}:{self.tz}"
        return cached(self.cache, "archive", key, call)

    def rain_as_issued(self, place, first: date, last: date) -> dict:
        return self._archive("rain_as_issued", place, first, last,
                             lambda: self.fetch.fetch_rain_as_issued(place, first, last, self.tz))

    def heat_as_issued(self, place, first: date, last: date) -> dict:
        return self._archive(f"heat_as_issued:{len(om.AS_ISSUED_MODELS)}models", place, first, last,
                             lambda: self.fetch.fetch_heat_as_issued(place, first, last, self.tz))

    def observed_daily(self, place, first: date, last: date) -> dict:
        return self._archive("observed", place, first, last,
                             lambda: self.fetch.fetch_observed_daily(place, first, last, self.tz))

    def river_archive(self, lat: float, lon: float, first: date, last: date, model: str) -> dict:
        cell = river_cell(lat, lon)
        return self._archive(f"river:{model}", cell, first, last,
                             lambda: self.fetch.fetch_river_discharge_archive(cell, first, last, model))
