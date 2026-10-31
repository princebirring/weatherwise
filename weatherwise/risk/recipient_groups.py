"""One warning per group of similar people, so AI cost grows with groups, not people (plan §11)."""

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Subscriber:
    id: str  # hashed phone number, never the raw number
    area_ids: tuple[str, ...]
    language: str
    role: str  # farmer | household | officer | family
    crop: str | None = None
    water_source: str | None = None


@dataclass(frozen=True)
class RecipientGroup:
    """People who get the same warning text: same area, language, crop and water source."""

    area_id: str
    language: str
    crop: str | None
    water_source: str | None


def recipient_groups_for_area(
    subscribers: list[Subscriber], area_id: str
) -> dict[RecipientGroup, list[str]]:
    """Subscriber IDs registered for area_id, grouped so each group gets one warning."""
    groups: dict[RecipientGroup, list[str]] = defaultdict(list)
    for s in subscribers:
        if area_id in s.area_ids:
            groups[RecipientGroup(area_id, s.language, s.crop, s.water_source)].append(s.id)
    return dict(groups)
