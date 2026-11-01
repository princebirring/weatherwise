"""Every district of a country with its official website. The district list is OpenStreetMap's
admin boundaries at the level the country's rules give; the website is Wikidata's "official
website" (P856) for the district each boundary links to. No district names are typed anywhere."""

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from weatherwise.https import urlopen
from weatherwise.places.geocoding import USER_AGENT
from weatherwise.shelters import OsmHealthFacilities

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_BATCH = 200


@dataclass(frozen=True)
class District:
    name: str
    wikidata: str
    lat: float | None    # centre of the boundary, for checking that a shelter lies in the district
    lon: float | None
    website: str | None


def _post_json(url: str, data: dict, timeout: float = 120) -> object:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _get_json(url: str, params: dict, timeout: float = 60) -> object:
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def osm_districts(osm_country: str, admin_level: int, post_json: Callable = _post_json) -> list[dict]:
    """[{name, wikidata, lat, lon}] for every admin boundary at admin_level inside the country."""
    query = (f'[out:json][timeout:110];area["ISO3166-1"="{osm_country}"][admin_level=2]->.c;'
             f'rel(area.c)[boundary=administrative][admin_level={admin_level}];out tags center;')
    last_error: Exception | None = None
    for url in OsmHealthFacilities.MIRRORS:
        try:
            elements = post_json(url, {"data": query})["elements"]
            break
        except Exception as e:
            last_error = e
    else:
        raise ConnectionError(f"all Overpass mirrors failed: {last_error}")
    return [
        {"name": e["tags"].get("name:en") or e["tags"].get("name", ""), "wikidata": e["tags"].get("wikidata", ""),
         "lat": e.get("center", {}).get("lat"), "lon": e.get("center", {}).get("lon")}
        for e in elements
    ]


def official_websites(wikidata_ids: list[str], get_json: Callable = _get_json) -> dict[str, str]:
    """Wikidata id -> official website, for the ids that have one."""
    ids = [q for q in wikidata_ids if q]
    sites: dict[str, str] = {}
    for i in range(0, len(ids), WIKIDATA_BATCH):
        values = " ".join(f"wd:{q}" for q in ids[i:i + WIKIDATA_BATCH])
        sparql = f"SELECT ?d ?site WHERE {{ VALUES ?d {{ {values} }} ?d wdt:P856 ?site. }}"
        rows = get_json(WIKIDATA_SPARQL, {"query": sparql, "format": "json"})["results"]["bindings"]
        for row in rows:
            sites.setdefault(row["d"]["value"].rsplit("/", 1)[1], row["site"]["value"])
    return sites


def list_districts(sources: dict, post_json: Callable = _post_json, get_json: Callable = _get_json) -> list[District]:
    found = osm_districts(sources["osm_country"], sources["district_admin_level"], post_json)
    sites = official_websites([d["wikidata"] for d in found], get_json)
    return sorted((District(d["name"], d["wikidata"], d["lat"], d["lon"], sites.get(d["wikidata"]))
                   for d in found), key=lambda d: d.name)
