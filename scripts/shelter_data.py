"""Developer tool: builds the verified shelter list for a country from official district disaster
plans (weatherwise/shelter_data/). Runs ahead of time; the website only reads the finished CSV.

    find      every district + its website, and its plan if the site has one
              -> data/shelter_sources_<iso>.csv
    fetch     download the plans found -> cache/shelter_plans/<iso>/<sha256>.pdf
    extract   Claude on Bedrock lists the shelters each plan names (needs CLIMATE_AGENT_MODEL_ID)
              -> data/review/shelters_<iso>_candidates.csv (a person approves each row)
    approve   approved, complete rows -> data/shelters_<iso>.csv
    coverage  how much of the country each step reached

Usage:
    uv run python scripts/shelter_data.py find --country in
    uv run python scripts/shelter_data.py fetch --country in
    uv run python scripts/shelter_data.py extract --country in --limit 5
    uv run python scripts/shelter_data.py approve --country in --checked-by "Name"
    uv run python scripts/shelter_data.py coverage --country in
"""

import argparse
import collections
import hashlib
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from weatherwise.https import urlopen  # noqa: E402
from weatherwise.rules import DATA_ROOT, load_rules  # noqa: E402
from weatherwise.shelter_data import shelter_sources  # noqa: E402
from weatherwise.shelter_data.districts import list_districts  # noqa: E402
from weatherwise.shelter_data.finder import BROWSER_AGENT, find_plan  # noqa: E402
from weatherwise.shelter_data.review import add_candidates, approve, read_csv, write_csv  # noqa: E402

SOURCE_FIELDS = ["district", "wikidata", "lat", "lon", "website", "status", "site", "plan_title", "plan_url",
                 "checked_on", "plan_sha256", "fetch_status", "pages", "pages_with_text", "extract_status",
                 "drafts", "dropped"]
MAX_PDF_BYTES = 80_000_000
LOCATE_MAX_KM = 80.0   # a draft's geocoded point must be this close to the district centre


def sources_path(country: str) -> Path:
    return DATA_ROOT / f"shelter_sources_{country}.csv"


def candidates_path(country: str) -> Path:
    return DATA_ROOT / "review" / f"shelters_{country}_candidates.csv"


def plans_dir(country: str) -> Path:
    return ROOT / "cache" / "shelter_plans" / country


def cmd_find(args, sources: dict) -> None:
    districts = list_districts(sources)
    if args.limit:
        districts = districts[: args.limit]
    print(f"{len(districts)} districts; {sum(1 for d in districts if d.website)} with an official website")

    def one(d):
        link = find_plan(d.website, sources)
        return {"district": d.name, "wikidata": d.wikidata, "lat": d.lat, "lon": d.lon, "website": d.website or "",
                "status": link.status, "site": link.site or "", "plan_title": link.title or "",
                "plan_url": link.url or "", "checked_on": date.today().isoformat()}

    rows = []
    with ThreadPoolExecutor(args.workers) as pool:
        for i, row in enumerate(pool.map(one, districts), 1):
            rows.append(row)
            if i % 50 == 0:
                print(i, dict(collections.Counter(r["status"] for r in rows)), flush=True)
    write_csv(sources_path(args.country), rows, SOURCE_FIELDS)
    print(dict(collections.Counter(r["status"] for r in rows)), "->", sources_path(args.country).relative_to(ROOT))


def download_pdf(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_AGENT})
    with urlopen(req, timeout=120) as resp:
        body = resp.read(MAX_PDF_BYTES + 1)
    if len(body) > MAX_PDF_BYTES:
        raise ValueError("larger than the size limit")
    if not body.startswith(b"%PDF"):
        raise ValueError("not a PDF")
    return body


def cmd_fetch(args, sources: dict) -> None:
    rows = read_csv(sources_path(args.country))
    folder = plans_dir(args.country)
    folder.mkdir(parents=True, exist_ok=True)

    def one(row):
        if row["status"] != "plan_found" or (row.get("plan_sha256") and (folder / f"{row['plan_sha256']}.pdf").exists()):
            return row
        try:
            body = download_pdf(row["plan_url"])
        except Exception as e:
            return {**row, "fetch_status": f"failed: {type(e).__name__} {e}"[:120]}
        sha = hashlib.sha256(body).hexdigest()
        (folder / f"{sha}.pdf").write_bytes(body)
        return {**row, "plan_sha256": sha, "fetch_status": "ok"}

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(one, rows))
    write_csv(sources_path(args.country), rows, SOURCE_FIELDS)
    print(dict(collections.Counter((r.get("fetch_status") or "-").split(":")[0] for r in rows if r["status"] == "plan_found")))


def cmd_extract(args, sources: dict) -> None:
    from weatherwise.agents.orchestrator import bedrock_model
    from weatherwise.places.geocoding import NominatimGeocoder
    from weatherwise.shelter_data.extraction import extract_shelters, locate, pdf_pages

    model, geocoder = bedrock_model(), NominatimGeocoder()
    rows = read_csv(sources_path(args.country))
    todo = [r for r in rows if r.get("fetch_status") == "ok" and not r.get("extract_status")
            and (not args.district or r["district"] in args.district)]
    for row in todo[: args.limit or None]:
        try:
            pages = pdf_pages(plans_dir(args.country) / f"{row['plan_sha256']}.pdf")
        except Exception as e:
            row["extract_status"] = f"unreadable: {type(e).__name__}"
            continue
        row["pages"], row["pages_with_text"] = len(pages), sum(1 for p in pages if p.strip())
        if not row["pages_with_text"]:
            row["extract_status"] = "scanned_needs_ocr"
            continue
        result = extract_shelters(pages, sources["shelter_words"], model)
        centre = (float(row["lat"]), float(row["lon"])) if row["lat"] and row["lon"] else None
        drafts = []
        for d in result.drafts:
            where = locate(d, row["district"], centre, args.country, geocoder, LOCATE_MAX_KM)
            drafts.append({
                "name": d.name, "type": d.place_type, "lat": where[0] if where else "", "lon": where[1] if where else "",
                "location_found": where[2] if where else "", "hazards": ";".join(d.hazards), "district": row["district"],
                "village_or_ward": d.village_or_ward, "capacity": d.capacity or "", "contact": "",
                "source": f"{row['plan_title']} (district disaster management plan), p.{d.page}: {row['plan_url']}",
                "page": d.page, "quote": d.quote, "plan_url": row["plan_url"], "plan_sha256": row["plan_sha256"],
            })
        added = add_candidates(candidates_path(args.country), drafts)
        row.update(extract_status="drafts_added" if drafts else "no_shelters_named", drafts=added, dropped=result.dropped)
        print(f"{row['district']}: {len(pages)} pages, {result.pages_sent} sent, {added} drafts, {result.dropped} dropped",
              flush=True)
        write_csv(sources_path(args.country), rows, SOURCE_FIELDS)
    write_csv(sources_path(args.country), rows, SOURCE_FIELDS)


def cmd_approve(args, sources: dict) -> None:
    rules = load_rules(args.country)
    result = approve(candidates_path(args.country), DATA_ROOT / f"shelters_{args.country}.csv", date.today(),
                     args.checked_by, rules["shelters"]["recheck_days"])
    print(f"added {len(result.added)}, already listed {len(result.already_listed)}, not ready {len(result.not_ready)}")
    for name, issues in result.not_ready:
        print(f"  not ready: {name}: {'; '.join(issues)}")


def cmd_coverage(args, sources: dict) -> None:
    rows = read_csv(sources_path(args.country))
    drafts = read_csv(candidates_path(args.country))
    shelters = read_csv(DATA_ROOT / f"shelters_{args.country}.csv")
    n = len(rows) or 1

    def line(label, count):
        print(f"  {label:38} {count:5}  ({count / n:.0%} of districts)")

    print(f"{args.country.upper()}: {len(rows)} districts")
    line("official website listed", sum(1 for r in rows if r["website"]))
    line("website reachable", sum(1 for r in rows if r["status"] in ("plan_found", "no_plan_found")))
    line("plan found on the website", sum(1 for r in rows if r["status"] == "plan_found"))
    line("plan downloaded", sum(1 for r in rows if r.get("fetch_status") == "ok"))
    line("plan read (has text)", sum(1 for r in rows if r.get("extract_status") in ("drafts_added", "no_shelters_named")))
    line("plan names shelters", sum(1 for r in rows if r.get("extract_status") == "drafts_added"))
    line("district has a verified shelter", len({s["district"] for s in shelters}))
    print(f"  drafts: {len(drafts)} ({sum(1 for d in drafts if d['status'] == 'approved')} approved, "
          f"{sum(1 for d in drafts if d['status'] == 'pending')} waiting); verified shelters: {len(shelters)}")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("find", "fetch", "extract", "approve", "coverage"):
        s = sub.add_parser(name)
        s.add_argument("--country", required=True)
        if name in ("find", "fetch"):
            s.add_argument("--workers", type=int, default=10)
        if name in ("find", "extract"):
            s.add_argument("--limit", type=int)
        if name == "extract":
            s.add_argument("--district", action="append", help="only these districts (repeatable)")
        if name == "approve":
            s.add_argument("--checked-by", required=True)
    args = p.parse_args()
    sources = shelter_sources(load_rules(args.country))
    {"find": cmd_find, "fetch": cmd_fetch, "extract": cmd_extract, "approve": cmd_approve,
     "coverage": cmd_coverage}[args.command](args, sources)


if __name__ == "__main__":
    main()
