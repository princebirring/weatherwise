"""Open-Meteo client: ensemble forecast, river discharge, recent observations, normals.

APIs used:
- Ensemble API (ECMWF IFS 0.25°, 51 runs): daily max temperature, feels-like max, rain
- Flood API (GloFAS, 51 runs): daily river discharge, forecast and history
- Forecast API: past rain and current soil moisture (not in the ensemble)
- Historical API (ERA5): 1991-2020 daily max temperature, for "normal" values
- Previous Runs API: forecasts as issued days earlier, from several models (replays, and
  each model's recent errors for the forecast correction)

fetch_* functions take any place with .lat and .lon (an Area or a RainPoint).
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

from weatherwise.https import urlopen
from weatherwise.risk.forecast_agreement import MIN_FORECAST_RUNS
from weatherwise.risk.models import Area, EnsembleForecast, ForecastDataMissing, RainPoint

Place = Area | RainPoint

ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

ENSEMBLE_MODEL = "ecmwf_ifs025"
ENSEMBLE_VARIABLES = (
    "temperature_2m_max", "temperature_2m_mean", "apparent_temperature_max", "precipitation_sum",
)

# River models: reconstructed past flow ("what happened"), and the archive of each day's forecast.
RIVER_REANALYSIS_MODEL = "consolidated_v4"
RIVER_FORECAST_ARCHIVE_MODEL = "forecast_v4"

# Global models whose past forecasts are archived. Together they act as a 7-run ensemble.
AS_ISSUED_MODELS = (
    "ecmwf_ifs025", "gfs_seamless", "icon_seamless", "gem_seamless",
    "jma_seamless", "cma_grapes_global", "bom_access_global",
)
MAX_PREVIOUS_DAY = 7  # the archive keeps forecasts issued up to 7 days earlier


class WeatherDataUnavailable(Exception):
    """The weather service could not be reached or returned an error."""


def _with_api_key(url: str, params: dict) -> tuple[str, dict]:
    """With OPEN_METEO_API_KEY set, use the paid (commercial) hosts: same API, own rate limits.
    The free hosts are shared and rate-limited, which a busy demo day can hit."""
    key = os.environ.get("OPEN_METEO_API_KEY")
    if not key:
        return url, params
    return url.replace("https://", "https://customer-", 1), {**params, "apikey": key}


def _get_json(url: str, params: dict, retries: int = 5, timeout: float = 30) -> dict | list:
    """GET with retries. Rate limits (HTTP 429) back off longer: 5, 10, 20, 40 s."""
    url, params = _with_api_key(url, params)
    query = urllib.parse.urlencode(params, safe=",")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(f"{url}?{query}", timeout=timeout) as resp:
                data = json.load(resp)
            if isinstance(data, dict) and data.get("error"):
                raise WeatherDataUnavailable(data.get("reason", "unknown error"))
            return data
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 400:
                raise WeatherDataUnavailable(f"{url}: bad request") from e
            time.sleep(5 * 2**attempt if e.code == 429 else 2**attempt)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_error = e
            time.sleep(2**attempt)
    raise WeatherDataUnavailable(f"{url}: {last_error}")


# ---- Fetch: raw JSON ------------------------------------------------------------


def fetch_ensemble_forecast(
    place: Place, timezone: str, days: int = 15, variables: tuple[str, ...] = ENSEMBLE_VARIABLES
) -> dict:
    return _get_json(
        ENSEMBLE_URL,
        {
            "latitude": place.lat,
            "longitude": place.lon,
            "daily": ",".join(variables),
            "models": ENSEMBLE_MODEL,
            "timezone": timezone,
            "forecast_days": days,
        },
    )


def fetch_river_discharge_forecast(area: Area, days: int = 10) -> dict:
    return _get_json(
        FLOOD_URL,
        {
            "latitude": area.lat,
            "longitude": area.lon,
            "daily": "river_discharge",
            "ensemble": "true",
            "forecast_days": days,
        },
    )


def fetch_recent_conditions(area: Area, timezone: str, past_days: int = 30) -> dict:
    return _get_json(
        FORECAST_URL,
        {
            "latitude": area.lat,
            "longitude": area.lon,
            "daily": "precipitation_sum,temperature_2m_mean",
            "hourly": "soil_moisture_0_to_7cm",
            "past_days": past_days,
            "forecast_days": 1,
            "timezone": timezone,
        },
    )


def fetch_historical_tmax(
    area: Area, timezone: str, first_year: int = 1991, last_year: int = 2020
) -> dict:
    return _get_json(
        HISTORICAL_URL,
        {
            "latitude": area.lat,
            "longitude": area.lon,
            "daily": "temperature_2m_max",
            "start_date": f"{first_year}-01-01",
            "end_date": f"{last_year}-12-31",
            "timezone": timezone,
        },
        timeout=90,
    )


def fetch_historical_daily(
    place: Place, timezone: str, variable: str, first_year: int = 1991, last_year: int = 2020
) -> dict:
    """Decades of one daily variable (ERA5): mean temperature for the Excess Heat Factor
    baseline, rain for the place's unusual-rain line."""
    return _get_json(
        HISTORICAL_URL,
        {
            "latitude": place.lat,
            "longitude": place.lon,
            "daily": variable,
            "start_date": f"{first_year}-01-01",
            "end_date": f"{last_year}-12-31",
            "timezone": timezone,
        },
        timeout=90,
    )


def fetch_historical_river_discharge(area: Area, first_year: int, last_year: int) -> dict:
    """Reconstructed daily river flow ("what happened") for whole years."""
    return fetch_river_discharge_archive(
        area, date(first_year, 1, 1), date(last_year, 12, 31), RIVER_REANALYSIS_MODEL
    )


def fetch_river_discharge_archive(area: Area, first_day: date, last_day: date, model: str) -> dict:
    """Past daily river flow from one river model (reanalysis or forecast archive)."""
    return _get_json(
        FLOOD_URL,
        {
            "latitude": area.lat,
            "longitude": area.lon,
            "daily": "river_discharge",
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "models": model,
        },
        timeout=90,
    )


def fetch_timezone(lat: float, lon: float) -> str:
    """The IANA time zone at a point (e.g. "Asia/Kolkata"), so no country file needs one."""
    data = _get_json(FORECAST_URL, {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max",
                                    "forecast_days": 1, "timezone": "auto"})
    return data["timezone"]


def fetch_elevation(lat: float, lon: float) -> float:
    """Ground elevation in metres (Copernicus DEM, ~90 m)."""
    return _get_json(ELEVATION_URL, {"latitude": lat, "longitude": lon})["elevation"][0]


def fetch_observed_daily(place: Place, first_day: date, last_day: date, timezone: str) -> dict:
    """What actually happened (ERA5 reanalysis): daily max temp, feels-like max, rain."""
    return _get_json(
        HISTORICAL_URL,
        {
            "latitude": place.lat,
            "longitude": place.lon,
            "daily": "temperature_2m_max,temperature_2m_mean,apparent_temperature_max,precipitation_sum",
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "timezone": timezone,
        },
        timeout=90,
    )


def fetch_heat_as_issued(place: Place, first_day: date, last_day: date, timezone: str,
                         models: tuple[str, ...] = AS_ISSUED_MODELS,
                         max_previous_day: int = MAX_PREVIOUS_DAY) -> dict:
    """Hourly temperature and feels-like forecasts for past days, as issued 1 to
    max_previous_day days earlier."""
    variables = [
        f"{v}_previous_day{k}"
        for v in ("temperature_2m", "apparent_temperature")
        for k in range(1, max_previous_day + 1)
    ]
    return _get_json(
        PREVIOUS_RUNS_URL,
        {
            "latitude": place.lat,
            "longitude": place.lon,
            "hourly": ",".join(variables),
            "models": ",".join(models),
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "timezone": timezone,
        },
        timeout=120,
    )


def fetch_river_discharge_many(places: list, first_day: date, last_day: date, model: str) -> list[dict]:
    """Past daily river flow for several points in one request (one response per point)."""
    data = _get_json(
        FLOOD_URL,
        {
            "latitude": ",".join(f"{p.lat}" for p in places),
            "longitude": ",".join(f"{p.lon}" for p in places),
            "daily": "river_discharge",
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "models": model,
        },
        timeout=90,
    )
    return data if isinstance(data, list) else [data]


def fetch_rain_as_issued(place: Place, first_day: date, last_day: date, timezone: str) -> dict:
    """Hourly rain forecasts for past days, as issued 1-7 days earlier, from AS_ISSUED_MODELS."""
    variables = [f"precipitation_previous_day{k}" for k in range(1, MAX_PREVIOUS_DAY + 1)]
    return _get_json(
        PREVIOUS_RUNS_URL,
        {
            "latitude": place.lat,
            "longitude": place.lon,
            "hourly": ",".join(variables),
            "models": ",".join(AS_ISSUED_MODELS),
            "start_date": first_day.isoformat(),
            "end_date": last_day.isoformat(),
            "timezone": timezone,
        },
        timeout=120,
    )


# ---- Parse: raw JSON -> engine types ------------------------------------------------


NON_NEGATIVE_VARIABLES = {"precipitation_sum", "river_discharge"}


def parse_ensemble(raw: dict, variable: str) -> EnsembleForecast:
    """All forecast runs for one daily variable: the control run plus each member.

    Days past the model's range (every run empty) are dropped from the end; gaps
    inside the range are kept, so the engine reports them as missing data. Tiny
    negative rain or river values (model rounding) are set to 0.
    """
    daily = raw["daily"]
    if variable not in daily:
        raise KeyError(f"{variable} not in response")
    keys = [variable] + sorted(k for k in daily if k.startswith(f"{variable}_member"))
    clamp = variable in NON_NEGATIVE_VARIABLES

    rows = []
    for i in range(len(daily["time"])):
        row = tuple(daily[k][i] for k in keys)
        if clamp:
            row = tuple(None if v is None else max(v, 0.0) for v in row)
        rows.append(row)
    while rows and all(v is None for v in rows[-1]):
        rows.pop()

    dates = tuple(date.fromisoformat(d) for d in daily["time"][: len(rows)])
    return EnsembleForecast(dates=dates, values=tuple(rows))


def parse_recent_conditions(
    raw: dict, today: date, dry_day_max_mm: float
) -> tuple[int, float | None]:
    """(dry days in a row before today, latest soil moisture in m3/m3)."""
    past = [
        mm
        for day, mm in zip(raw["daily"]["time"], raw["daily"]["precipitation_sum"], strict=True)
        if date.fromisoformat(day) < today
    ]
    dry_days = 0
    for mm in reversed(past):
        if mm is None or mm >= dry_day_max_mm:
            break
        dry_days += 1

    soil = [v for v in raw["hourly"]["soil_moisture_0_to_7cm"] if v is not None]
    return dry_days, (soil[-1] if soil else None)


def parse_past_daily_means(raw: dict, before: date, days: int = 30) -> list[float]:
    """The last `days` observed daily mean temperatures before a date (gaps dropped)."""
    values = [
        v for d, v in zip(raw["daily"]["time"], raw["daily"]["temperature_2m_mean"], strict=True)
        if date.fromisoformat(d) < before and v is not None
    ]
    return values[-days:]


def parse_normal_tmax(raw: dict, window_days: int = 7) -> dict[str, float]:
    """Normal daily max temperature per calendar day ("MM-DD").

    Mean over all years, smoothed over +/- window_days around each date.
    Note: ERA5 is a ~25 km grid average and runs cooler than station records.
    """
    by_day: dict[int, list[float]] = defaultdict(list)
    for day, value in zip(raw["daily"]["time"], raw["daily"]["temperature_2m_max"], strict=True):
        if value is None:
            continue
        d = date.fromisoformat(day)
        if (d.month, d.day) == (2, 29):
            continue
        by_day[date(2001, d.month, d.day).timetuple().tm_yday].append(value)

    normals = {}
    for doy in range(1, 366):
        window = [
            v
            for offset in range(-window_days, window_days + 1)
            for v in by_day[(doy - 1 + offset) % 365 + 1]
        ]
        md = date.fromordinal(date(2001, 1, 1).toordinal() + doy - 1).strftime("%m-%d")
        if not window:
            raise ValueError(f"no historical data around {md}")
        normals[md] = round(sum(window) / len(window), 2)
    normals["02-29"] = normals["02-28"]
    return normals


def yearly_peak_flows(raw: dict) -> dict[int, float]:
    """Each year's highest daily river flow."""
    peaks: dict[int, float] = {}
    for day, value in zip(raw["daily"]["time"], raw["daily"]["river_discharge"], strict=True):
        if value is None:
            continue
        year = int(day[:4])
        peaks[year] = max(peaks.get(year, value), value)
    return peaks


def parse_flood_level(raw: dict, return_period_years: float) -> float:
    """The area's flood level: the yearly peak flow reached about once every N years.

    Estimated from the area's own history with Weibull plotting positions (rank / (n + 1)),
    a standard hydrology method. Ours, not an official danger mark.
    """
    peaks = sorted(yearly_peak_flows(raw).values())
    n = len(peaks)
    if n < 10:
        raise ValueError(f"only {n} years of river history")
    position = (1 - 1 / return_period_years) * (n + 1)  # 1-based rank of the target flow
    if position <= 1:
        return round(peaks[0], 1)
    if position >= n:
        return round(peaks[-1], 1)
    lower = int(position)
    fraction = position - lower
    return round(peaks[lower - 1] + fraction * (peaks[lower] - peaks[lower - 1]), 1)


def parse_daily_values(raw: dict, variable: str) -> dict[date, float]:
    """A single daily series (e.g. past river flow) keyed by date; missing days left out."""
    return {
        date.fromisoformat(day): value
        for day, value in zip(raw["daily"]["time"], raw["daily"][variable], strict=True)
        if value is not None
    }


_COMBINE_HOURS = {"sum": lambda vs: round(sum(max(v, 0.0) for v in vs), 1),
                  "max": lambda vs: round(max(vs), 1),
                  "mean": lambda vs: round(sum(vs) / len(vs), 2)}


def _hours_by_day(hourly: dict) -> dict[str, list[int]]:
    hours: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(hourly["time"]):
        hours[t[:10]].append(i)
    return hours


def _issued_value(hourly: dict, hours: list[int], variable: str, previous_day: int, model: str | None,
                  daily: str) -> float | None:
    """One model's forecast for one day, issued previous_day days earlier (None if incomplete).
    model None: a one-model request, whose columns carry no model name."""
    series = hourly.get(f"{variable}_previous_day{previous_day}" + (f"_{model}" if model else ""))
    values = [series[i] for i in hours] if series is not None else []
    return None if len(values) != 24 or any(v is None for v in values) else _COMBINE_HOURS[daily](values)


def parse_as_issued(raw: dict, issue_date: date, variable: str, daily: str) -> EnsembleForecast:
    """Daily forecasts of one hourly variable the way they looked on the morning of issue_date.

    daily: "sum" (rain), "max" or "mean" (temperature). The morning scan cannot use runs issued later
    that day, so day D + k uses forecasts issued k + 1 days before it ("previous_day{k+1}"):
    about half a day older than what we would really have had, conservative on purpose.
    Each archived model is one forecast run. Trailing days with too few models are dropped.
    """
    hourly = raw["hourly"]
    hours_by_day = _hours_by_day(hourly)
    dates, rows = [], []
    for k in range(MAX_PREVIOUS_DAY):
        target = issue_date + timedelta(days=k)
        hours = hours_by_day.get(target.isoformat(), [])
        dates.append(target)
        rows.append(tuple(_issued_value(hourly, hours, variable, k + 1, model, daily)
                          for model in AS_ISSUED_MODELS))

    while rows and sum(v is not None for v in rows[-1]) < MIN_FORECAST_RUNS:
        rows.pop()
        dates.pop()
    if not rows:
        raise ForecastDataMissing(f"{issue_date}: fewer than {MIN_FORECAST_RUNS} archived models")
    return EnsembleForecast(dates=tuple(dates), values=tuple(rows))


def parse_day_ahead(raw: dict, variable: str, daily: str,
                    models: tuple[str, ...] = AS_ISSUED_MODELS) -> dict[date, tuple[float | None, ...]]:
    """Every day in an archive, as forecast the day before: one value per model, in order."""
    hourly = raw["hourly"]
    names: tuple[str | None, ...] = (None,) if len(models) == 1 else models  # one model: no suffix
    return {
        date.fromisoformat(day): tuple(_issued_value(hourly, hours, variable, 1, m, daily) for m in names)
        for day, hours in _hours_by_day(hourly).items()
    }


def parse_rain_as_issued(raw: dict, issue_date: date) -> EnsembleForecast:
    return parse_as_issued(raw, issue_date, "precipitation", "sum")
