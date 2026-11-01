"""Shelters named in a district disaster plan, as drafts for a person to approve.

Only pages that mention a shelter word (country rules, any of its languages) go to the model.
The model (Claude on Bedrock, through a Strands agent) returns typed rows, each with the page
number and the exact words on that page that name the place. Code then drops every row whose
quote is not on that page, or whose name is not in its quote: the model cannot add a shelter the
plan does not contain. Locations come from the geocoder and must fall inside the district;
otherwise the reviewer adds them.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from weatherwise.places.geocoding import Geocoder, distance_km

MAX_CHARS_PER_CALL = 15000

SYSTEM_PROMPT = """You read pages of an official district disaster management plan and list the places
it names as shelters for people: relief camps, relief centres, cyclone shelters, flood shelters,
evacuation centres, temporary shelters (often schools or community halls), and cooling centres.

Rules:
- Only places the text itself names as a shelter, camp or centre for people. Not offices, control
  rooms, godowns, hospitals or equipment lists.
- name: exactly as written, in the plan's language and spelling. Do not translate.
- place_type: "cooling_center" only if the text says it is for heat; otherwise "shelter".
- hazards: only the hazards the text gives for that place (flood, cyclone, heat, other). Leave the
  list empty if the text does not say.
- page: the number from the "=== PAGE n ===" line above the text.
- quote: copy the exact words from that page that name the place (one table row or one line).
- If the pages name no shelters, return an empty list. Never guess."""


class ShelterDraft(BaseModel):
    name: str = Field(description="The place's name exactly as written in the plan")
    place_type: Literal["shelter", "cooling_center"]
    village_or_ward: str = Field("", description="Village, town or ward as written, if given")
    hazards: list[Literal["flood", "cyclone", "heat", "other"]] = Field(default_factory=list)
    capacity: int | None = Field(None, description="Number of people, if the plan gives it")
    page: int = Field(description="Page number from the === PAGE n === marker")
    quote: str = Field(description="Exact words from that page that name the place")


class ShelterDrafts(BaseModel):
    shelters: list[ShelterDraft]


@dataclass(frozen=True)
class Extraction:
    drafts: list[ShelterDraft]
    pages: int                 # pages in the PDF
    pages_with_text: int       # 0 means a scanned plan: needs OCR, nothing extracted
    pages_sent: int
    dropped: int               # rows the model returned that failed the page/quote check


def pdf_pages(path: Path) -> list[str]:
    """Text of each page ("" for a page with no text layer)."""
    from pypdf import PdfReader  # dev dependency: only the list builder reads PDFs

    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font-encoding notes on almost every government PDF
    return [page.extract_text() or "" for page in PdfReader(path).pages]


def _squash(text: str) -> str:
    """Compare without whitespace or case: PDF text breaks lines and spaces table cells oddly."""
    return re.sub(r"\s+", "", text).casefold()


def is_grounded(draft: ShelterDraft, pages: list[str]) -> bool:
    if not 1 <= draft.page <= len(pages) or not draft.name.strip():
        return False
    quote = _squash(draft.quote)
    return bool(quote) and _squash(draft.name) in quote and quote in _squash(pages[draft.page - 1])


def batches(pages: list[str], shelter_words: list[str], max_chars: int = MAX_CHARS_PER_CALL) -> list[list[int]]:
    """Page numbers (1-based) that mention a shelter word, grouped to fit one model call each."""
    words = re.compile("|".join(re.escape(w) for w in shelter_words), re.I)
    groups: list[list[int]] = []
    size = 0
    for number, text in enumerate(pages, 1):
        if not words.search(text):
            continue
        if not groups or size + len(text) > max_chars:
            groups.append([])
            size = 0
        groups[-1].append(number)
        size += len(text)
    return groups


def extract_shelters(pages: list[str], shelter_words: list[str], model) -> Extraction:
    from strands import Agent  # local: tests and the website never load the agent stack here

    groups = batches(pages, shelter_words)
    kept: list[ShelterDraft] = []
    dropped = 0
    for group in groups:
        text = "\n\n".join(f"=== PAGE {n} ===\n{pages[n - 1]}" for n in group)
        agent = Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None)
        result = agent(f"List the shelters named on these pages.\n\n{text}", structured_output_model=ShelterDrafts)
        for draft in result.structured_output.shelters:
            if draft.page in group and is_grounded(draft, pages):
                kept.append(draft)
            else:
                dropped += 1
    return Extraction(kept, len(pages), sum(1 for p in pages if p.strip()), sum(len(g) for g in groups), dropped)


def locate(draft: ShelterDraft, district_name: str, centre: tuple[float, float] | None, country_code: str,
           geocoder: Geocoder, max_km: float) -> tuple[float, float, str] | None:
    """(lat, lon, what was found) inside the district, or None for the reviewer to fill in.
    The place itself is tried first; failing that, its village or ward (an approximate point that
    the reviewer must confirm)."""
    if centre is None:
        return None
    tries = [(f"{draft.name}, {draft.village_or_ward or district_name}", "place")]
    if draft.village_or_ward:
        tries.append((f"{draft.village_or_ward}, {district_name}", "village"))
        tries.append((draft.village_or_ward, "village"))
    for query, what in tries:
        try:
            candidates = geocoder.search(query, country_code)
        except Exception:  # noqa: S112 - geocoder down: leave it to the reviewer
            continue
        for c in candidates:
            if distance_km(centre[0], centre[1], c.lat, c.lon) <= max_km:
                return c.lat, c.lon, what
    return None
