# Shelters and cooling centers (Part 2)

`shelters_<country>.csv` (e.g. `shelters_in.csv`, one table for the country; the district column says where) holds **verified** places only (plan §6.5). A row is ignored unless it has:
name, type (`cooling_center` | `shelter`), lat, lon, hazards (`heat;flood;cyclone;other`), source
(district disaster plan / municipal list + page), checked_on, recheck_due.

- Past `recheck_due`, a place is hidden and the reply says "Call 1077". `recheck_due` is set
  `[shelters] recheck_days` after `checked_on` (rules/global.toml).
- OpenStreetMap shelter data is ODbL: keep it in a separate `shelters_osm_<country>.csv` with attribution.

## How the list is built

No government publishes shelters as data, but every Indian district must publish a disaster
management plan (Disaster Management Act 2005, s.31), and many plans name their relief camps.
`scripts/shelter_data.py` turns those plans into rows, ahead of time; the website only reads the
finished CSV. It works for any country with a `[shelter_sources]` section in its rules file.

| Step | Command | Writes |
|---|---|---|
| 1. Find every district's plan (district list from OpenStreetMap, website from Wikidata) | `find --country in` | `shelter_sources_in.csv` |
| 2. Download the plans | `fetch --country in` | `cache/shelter_plans/in/` (not committed) |
| 3. Claude on Bedrock lists the shelters each plan names, with page and exact quote; rows whose quote is not on that page are dropped | `extract --country in` | `review/shelters_in_candidates.csv` |
| 4. A person reviews each draft: set `status` to `approved` or `rejected`, fill in or correct `lat`, `lon`, `hazards` | (edit the CSV) | |
| 5. Approved, complete rows join the verified list, stamped with who checked them | `approve --country in --checked-by "Name"` | `shelters_in.csv` |
| Report how far each step reached | `coverage --country in` | |

`location_found` in the drafts says how a point was found: `place` (the building itself) or
`village` (the village centre; move the point to the building before approving). Empty means
the reviewer must add it. Re-running steps 1–3 never overwrites a draft a person has reviewed.
