from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Hazard(str, Enum):
    HEAT_WAVE = "heat_wave"
    HUMID_HEAT = "humid_heat"
    EXCESS_HEAT = "excess_heat"  # Excess Heat Factor: ours, self-calibrating to local climate
    HEAVY_RAIN = "heavy_rain"
    DRY_SPELL = "dry_spell"
    SOWING_RISK = "sowing_risk"
    RIVER_FLOOD = "river_flood"


class TerrainZone(str, Enum):
    """Terrain type used by official heat rules (IMD: plains, coast, hills). Rules that ignore terrain need no change."""

    PLAINS = "plains"
    COAST = "coast"
    HILLS = "hills"


@dataclass(frozen=True)
class RainPoint:
    """A point upstream of a river area where heavy rain gives early flood warning."""

    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Area:
    """A place we forecast for: a village, town, or city ward."""

    id: str
    name: str
    district: str
    terrain: TerrainZone
    lat: float
    lon: float


@dataclass(frozen=True)
class EnsembleForecast:
    """One daily weather variable for one area, from many forecast runs.

    values[day][run]; None means that run has no value for that day.
    """

    dates: tuple[date, ...]
    values: tuple[tuple[float | None, ...], ...]

    def __post_init__(self) -> None:
        if len(self.dates) != len(self.values):
            raise ValueError("dates and values must have the same length")


@dataclass(frozen=True)
class HazardDetection:
    """A hazard the forecast shows for an area. Not yet a message."""

    area_id: str
    hazard: Hazard
    severity: str
    first_day: date
    last_day: date
    days_ahead: int
    agreement: float  # share of forecast runs that agree, 0-1
    evidence: dict = field(default_factory=dict)


class ForecastDataMissing(Exception):
    """Too little forecast data to judge risk.

    Callers must not conclude "no risk" or send cancellations (plan §5.4).
    """
