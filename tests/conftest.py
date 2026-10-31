import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from weatherwise.risk.models import Area, EnsembleForecast, TerrainZone  # noqa: E402
from weatherwise.rules import load_rules, message_policy  # noqa: E402

ISSUE = date(2026, 4, 10)
RUNS = 10


@pytest.fixture(scope="session")
def rules() -> dict:
    return load_rules("in")


@pytest.fixture(scope="session")
def policy() -> dict:
    return message_policy("in")


@pytest.fixture
def akola() -> Area:
    return Area("akola", "Akola", "Akola", TerrainZone.PLAINS, 20.70, 77.00)


@pytest.fixture
def kharghar() -> Area:
    return Area("kharghar", "Kharghar", "Raigad", TerrainZone.COAST, 19.03, 73.07)


def forecast(daily: list[float | list[float | None]], start: date = ISSUE) -> EnsembleForecast:
    """Build a forecast. A number means every run has that value that day."""
    rows = [tuple(d) if isinstance(d, list) else (d,) * RUNS for d in daily]
    return EnsembleForecast(
        dates=tuple(start + timedelta(days=i) for i in range(len(rows))),
        values=tuple(rows),
    )


def runs_split(n_yes: int, yes: float, no: float) -> list[float]:
    """n_yes forecast runs at `yes`, the rest at `no`."""
    return [yes] * n_yes + [no] * (RUNS - n_yes)


def same_normal(f: EnsembleForecast, value: float) -> dict:
    return {d: value for d in f.dates}
