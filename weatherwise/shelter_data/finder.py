"""Finds a district's disaster management plan on its official website.

Looks at the pages the country's rules list (documents page, site search, disaster page), opens
categories whose name mentions disaster, and picks a document whose title has a disaster word AND
a plan word (in any of the country's languages) and no excluded word, preferring titles that name
the district level, then direct PDFs. Plain code, no AI:
a wrong pick only costs a wasted download, because nothing reaches the shelter list without a
person approving it.
"""

import html
import re
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from weatherwise.https import urlopen

LINK = re.compile(r'href="(https?://[^"?&#]+/(document|document-category)/[^"?&#]+)"[^>]*>([^<]{0,200})')
ROW = re.compile(r"<(tr|li)[^>]*>(.*?)</\1>", re.S)
PDF = re.compile(r'href="([^"]+\.pdf)"', re.I)
BROWSER_AGENT = "Mozilla/5.0 (compatible; WeatherWise shelter-plan finder)"


@dataclass(frozen=True)
class PlanLink:
    status: str            # plan_found | no_plan_found | site_down | no_website
    site: str | None = None
    title: str | None = None
    url: str | None = None


def fetch_page(url: str, timeout: float = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def site_addresses(website: str, domain_suffixes: list[str]) -> list[str]:
    """The listed address first (over https, without www.), then the same name under each of the
    country's government domains, since listed addresses go stale when a site moves."""
    host = urllib.parse.urlparse(website if "//" in website else "http://" + website).netloc.lower()
    host = host.removeprefix("www.").split(":")[0]
    stem = next((host.removesuffix(s) for s in domain_suffixes if host.endswith(s)), None)
    moved = [stem + s for s in domain_suffixes] if stem else []
    return list(dict.fromkeys(f"https://{h}" for h in [host, *moved]))


def _words(words: list[str]) -> re.Pattern:
    return re.compile("|".join(re.escape(w) for w in words), re.I)


def listed_items(page: str) -> list[tuple[str, str, str]]:
    """(kind, url, label) for document pages, categories and table/list rows with a PDF link."""
    items = []
    for url, kind, text in LINK.findall(page):
        slug = urllib.parse.unquote(url.rstrip("/").rsplit("/", 1)[1]).replace("-", " ")
        items.append((kind, url, f"{text.strip()} {slug}"))
    for _, row in ROW.findall(page):
        pdf = PDF.search(row)
        if pdf:
            text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", row)).split())
            items.append(("pdf", pdf.group(1), text[:300]))
    return items


def find_plan(website: str | None, sources: dict, fetch: Callable[[str], str] = fetch_page) -> PlanLink:
    if not website:
        return PlanLink("no_website")
    disaster, plan = _words(sources["disaster_words"]), _words(sources["plan_words"])
    district = _words(sources["district_words"])
    excluded = re.compile("|".join(rf"\b{re.escape(w)}\b" for w in sources["not_plan_words"]), re.I)

    def is_plan(label: str) -> bool:
        return bool(disaster.search(label) and plan.search(label) and not excluded.search(label))

    for base in site_addresses(website, sources["domain_suffixes"]):
        try:
            fetch(base + "/")
        except Exception:  # noqa: S112 - this address is down; try the next one
            continue
        found: list[tuple[str, str, str]] = []
        for path in sources["search_paths"]:
            try:
                found += listed_items(fetch(base + path))
            except Exception:  # noqa: S112 - a missing page is normal; try the next one
                continue
        for kind, url, label in list(found):
            if kind == "document-category" and disaster.search(label):
                try:
                    found += listed_items(fetch(url))
                except Exception:  # noqa: S112
                    continue
        plans = sorted((x for x in found if x[0] in ("pdf", "document") and is_plan(x[2])),
                       key=lambda x: (not district.search(x[2]), x[0] != "pdf"))
        if not plans:
            return PlanLink("no_plan_found", site=base)
        kind, url, label = plans[0]
        if kind == "document":
            try:
                pdfs = PDF.findall(fetch(url))
                url = pdfs[0] if pdfs else url
            except Exception:
                pass
        return PlanLink("plan_found", site=base, title=label[:200], url=url)
    return PlanLink("site_down")
