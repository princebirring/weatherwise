"""Drafts -> human approval -> data/shelters_<iso>.csv.

The drafts file (data/review/shelters_<iso>_candidates.csv) is edited by a person: set status to
"approved" or "rejected", fill in or correct lat, lon and hazards. Re-running the extraction adds
new drafts but never overwrites a row a person has already seen. Only approved rows with every
required field reach the shelter list, stamped with who checked them and when to re-check.
"""

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from weatherwise.shelters import PLACE_TYPE_FOR_HAZARD

CANDIDATE_FIELDS = ["status", "name", "type", "lat", "lon", "location_found", "hazards", "district",
                    "village_or_ward", "capacity", "contact", "source", "page", "quote", "plan_url",
                    "plan_sha256", "reviewer_note"]
SHELTER_FIELDS = ["name", "type", "lat", "lon", "hazards", "district", "source", "contact", "open_status",
                  "checked_on", "checked_by", "recheck_due"]
PLACE_TYPES = set(PLACE_TYPE_FOR_HAZARD.values())
HAZARDS = set(PLACE_TYPE_FOR_HAZARD)


def _key(row: dict) -> tuple[str, str, str]:
    return row["plan_sha256"], str(row["page"]), row["name"].strip().casefold()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_candidates(path: Path, new_rows: list[dict]) -> int:
    """Append drafts not seen before; rows already in the file (and any edits to them) stay as they are."""
    rows = read_csv(path)
    seen = {_key(r) for r in rows}
    added = [{**r, "status": "pending"} for r in new_rows if _key(r) not in seen]
    write_csv(path, rows + added, CANDIDATE_FIELDS)
    return len(added)


def problems(row: dict) -> list[str]:
    """What stops an approved draft from going on the shelter list."""
    found = [f"missing {k}" for k in ("name", "type", "lat", "lon", "hazards", "source") if not row.get(k, "").strip()]
    if row.get("type") and row["type"] not in PLACE_TYPES:
        found.append(f"type must be one of {sorted(PLACE_TYPES)}")
    if row.get("hazards") and not {h.strip() for h in row["hazards"].split(";")} <= HAZARDS:
        found.append(f"hazards must be from {sorted(HAZARDS)}, separated by ;")
    try:
        if not (-90 <= float(row.get("lat") or "x") <= 90 and -180 <= float(row.get("lon") or "x") <= 180):
            found.append("lat/lon out of range")
    except ValueError:
        if row.get("lat") and row.get("lon"):
            found.append("lat/lon must be numbers")
    return found


@dataclass
class Approval:
    added: list[str] = field(default_factory=list)
    already_listed: list[str] = field(default_factory=list)
    not_ready: list[tuple[str, list[str]]] = field(default_factory=list)


def approve(candidates_path: Path, shelters_path: Path, today: date, checked_by: str, recheck_days: int) -> Approval:
    if not checked_by.strip():
        raise ValueError("checked_by is required: the shelter list records who checked each place")
    shelters = read_csv(shelters_path)
    listed = {(s["name"].strip().casefold(), s["source"]) for s in shelters}
    result = Approval()
    for row in read_csv(candidates_path):
        if row["status"] != "approved":
            continue
        if issues := problems(row):
            result.not_ready.append((row["name"], issues))
            continue
        if (row["name"].strip().casefold(), row["source"]) in listed:
            result.already_listed.append(row["name"])
            continue
        shelters.append({**{k: row.get(k, "") for k in SHELTER_FIELDS}, "open_status": "",
                         "checked_on": today.isoformat(), "checked_by": checked_by,
                         "recheck_due": (today + timedelta(days=recheck_days)).isoformat()})
        listed.add((row["name"].strip().casefold(), row["source"]))
        result.added.append(row["name"])
    write_csv(shelters_path, shelters, SHELTER_FIELDS)
    return result
