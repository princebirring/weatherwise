# Shelters and cooling centers (Part 2)

`shelters_<country>.csv` (e.g. `shelters_in.csv`, one table for the country; the district column says where) holds **verified** places only (plan §6.5). A row is ignored unless it has:
name, type (`cooling_center` | `shelter`), lat, lon, hazards (`heat;flood;cyclone`), source
(district disaster plan / municipal list + page), checked_on, recheck_due.

- Re-check every 30 days in heat and monsoon seasons, 90 days otherwise. Past `recheck_due`,
  a place is hidden and the reply says "Call 1077".
- OpenStreetMap shelter data is ODbL: keep it in a separate `shelters_osm_<country>.csv` with attribution.
- Filled by the user (content checklist §15.3, item 1).
