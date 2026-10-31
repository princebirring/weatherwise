"""Forecast grid cells: the unit we fetch, cache and scan (plan §8.9).

Weather grid: 0.25 degrees (~25 km), the ECMWF ensemble resolution; ~150 villages per cell.
River grid: 0.05 degrees (~5 km), the GloFAS resolution, because rivers are narrow.
"""

from dataclasses import dataclass

WEATHER_GRID_DEG = 0.25
RIVER_GRID_DEG = 0.05


@dataclass(frozen=True)
class GridCell:
    lat: float  # cell centre
    lon: float
    size_deg: float

    @property
    def key(self) -> str:
        return f"{self.size_deg}:{self.lat:.2f}:{self.lon:.2f}"


def _snap(value: float, size: float) -> float:
    return round(round(value / size) * size, 4)


def grid_cell(lat: float, lon: float, size_deg: float = WEATHER_GRID_DEG) -> GridCell:
    return GridCell(_snap(lat, size_deg), _snap(lon, size_deg), size_deg)


def river_cell(lat: float, lon: float) -> GridCell:
    """The GloFAS cell containing the point. GloFAS cell centres sit at x.x25 / x.x75."""
    s = RIVER_GRID_DEG

    def centre(v: float) -> float:
        return round((v // s) * s + s / 2, 4)

    return GridCell(centre(lat), centre(lon), s)


def neighbour_ring(cell: GridCell) -> list[GridCell]:
    """The 8 cells around a cell (stage 2 of the scale path)."""
    s = cell.size_deg
    return [
        GridCell(round(cell.lat + dy * s, 4), round(cell.lon + dx * s, 4), s)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if (dy, dx) != (0, 0)
    ]
