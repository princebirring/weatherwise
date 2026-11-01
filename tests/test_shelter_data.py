"""Building the verified shelter list from district disaster plans: offline, no network, no AI."""

from datetime import date

import pytest

from tests.fake_model import ScriptedModel
from weatherwise.places.geocoding import AdminArea, PlaceCandidate
from weatherwise.rules import ConfigError
from weatherwise.shelter_data import shelter_sources
from weatherwise.shelter_data.districts import list_districts
from weatherwise.shelter_data.extraction import ShelterDraft, batches, extract_shelters, is_grounded, locate
from weatherwise.shelter_data.finder import find_plan, site_addresses
from weatherwise.shelter_data.review import add_candidates, approve, read_csv
from weatherwise.shelters import load_shelters


@pytest.fixture(scope="module")
def india(rules) -> dict:
    return shelter_sources(rules)


# A made-up second country: different domains, words and pages. Nothing in the code may assume India.
OTHER_COUNTRY = {
    "osm_country": "KE", "district_admin_level": 4, "domain_suffixes": [".go.ke"],
    "search_paths": ["/downloads/"], "disaster_words": ["disaster", "maafa"], "plan_words": ["plan", "mpango"],
    "not_plan_words": ["tender"], "district_words": ["county"], "shelter_words": ["evacuation centre", "kambi"],
}


def fake_site(pages: dict[str, str]):
    def fetch(url: str) -> str:
        if url not in pages:
            raise OSError(f"no page {url}")
        return pages[url]
    return fetch


# --- finder ---------------------------------------------------------------------------------

def test_plan_titled_only_in_marathi_is_found_in_a_category_table(india):
    category = "https://thane.gov.in/document-category/district-disaster/"
    site = fake_site({
        "https://thane.gov.in/": "<html>home</html>",
        "https://thane.gov.in/documents/": f'<a href="{category}">जिल्हा आपत्ती व्यवस्थापन</a>',
        category: '<table><tr><td>जिल्हा आपत्ती व्यवस्थापन आराखडा</td><td>24/02/2025</td>'
                  '<td><a href="https://cdn.example/uploads/2025/plan.pdf">पहा</a></td></tr></table>',
    })
    link = find_plan("http://www.thane.nic.in", india, site)
    assert link.status == "plan_found"
    assert link.url == "https://cdn.example/uploads/2025/plan.pdf"
    assert link.site == "https://thane.gov.in"   # stale listed address, found under the other domain


def test_document_page_is_followed_to_its_pdf_and_the_act_is_not_mistaken_for_a_plan(india):
    site = fake_site({
        "https://d.nic.in/": "home",
        "https://d.nic.in/?s=disaster+management+plan":
            '<a href="https://d.nic.in/document/disaster-management-act-2005/">Disaster Management Act</a>'
            '<a href="https://d.nic.in/document/district-disaster-management-plan-2025/">DDMP</a>',
        "https://d.nic.in/document/district-disaster-management-plan-2025/":
            '<a href="https://d.nic.in/uploads/ddmp.pdf">View</a>',
    })
    link = find_plan("https://d.nic.in", india, site)
    assert (link.status, link.url) == ("plan_found", "https://d.nic.in/uploads/ddmp.pdf")


def test_the_district_plan_beats_other_bodies_plans_on_the_same_site(india):
    site = fake_site({
        "https://s.gov.in/": "home",
        "https://s.gov.in/documents/":
            '<table><tr><td>Oil Spill Disaster Contingency Plan</td><td><a href="https://s.gov.in/oil.pdf">V</a></td></tr>'
            '<tr><td>Court Disaster Management Plan</td><td><a href="https://s.gov.in/court.pdf">V</a></td></tr>'
            '<tr><td>Disaster Management Plan 2024</td><td><a href="https://s.gov.in/old.pdf">V</a></td></tr>'
            '<tr><td>District Disaster Management Plan 2025</td><td><a href="https://s.gov.in/ddmp.pdf">V</a></td></tr></table>',
    })
    assert find_plan("https://s.gov.in", india, site).url == "https://s.gov.in/ddmp.pdf"


def test_site_down_and_no_website_and_no_plan_are_told_apart(india):
    assert find_plan(None, india, fake_site({})).status == "no_website"
    assert find_plan("https://gone.nic.in", india, fake_site({})).status == "site_down"
    assert find_plan("https://x.nic.in", india, fake_site({"https://x.nic.in/": "home"})).status == "no_plan_found"


def test_another_country_works_from_its_rules_alone():
    site = fake_site({
        "https://kisumu.go.ke/": "home",
        "https://kisumu.go.ke/downloads/": '<ul><li>Mpango wa Maafa 2025 <a href="https://kisumu.go.ke/m.pdf">PDF</a></li>'
                                           '<li>Disaster tender <a href="https://kisumu.go.ke/t.pdf">PDF</a></li></ul>',
    })
    assert site_addresses("http://www.kisumu.go.ke", [".go.ke"]) == ["https://kisumu.go.ke"]
    assert find_plan("http://www.kisumu.go.ke", OTHER_COUNTRY, site).url == "https://kisumu.go.ke/m.pdf"


def test_a_country_without_a_shelter_sources_section_fails_clearly():
    with pytest.raises(ConfigError, match="shelter_sources"):
        shelter_sources({})


# --- districts ------------------------------------------------------------------------------

def test_districts_come_from_osm_with_websites_from_wikidata(india):
    def post_json(url, data):
        assert "admin_level=5" in data["data"] and '"ISO3166-1"="IN"' in data["data"]
        return {"elements": [
            {"tags": {"name": "Wardha", "wikidata": "Q1"}, "center": {"lat": 20.7, "lon": 78.6}},
            {"tags": {"name": "Niuland", "wikidata": "Q2"}, "center": {"lat": 25.7, "lon": 93.8}},
        ]}

    def get_json(url, params):
        return {"results": {"bindings": [{"d": {"value": "http://www.wikidata.org/entity/Q1"},
                                          "site": {"value": "https://wardha.gov.in"}}]}}

    districts = list_districts(india, post_json, get_json)
    assert [(d.name, d.website) for d in districts] == [("Niuland", None), ("Wardha", "https://wardha.gov.in")]


# --- extraction -----------------------------------------------------------------------------

PAGES = [
    "Chapter 1 Introduction to the district",
    "Annexure 7: List of relief camps\n1  Z.P. School   Wadgaon   300 persons\n2  Community Hall   Pimpri   150",
    "Control room numbers 1077",
]


def draft(**kw) -> ShelterDraft:
    base = {"name": "Z.P. School", "place_type": "shelter", "village_or_ward": "Wadgaon", "page": 2,
            "quote": "1 Z.P. School Wadgaon 300 persons"}
    return ShelterDraft(**{**base, **kw})


def test_only_rows_whose_quote_is_on_their_page_are_kept():
    assert is_grounded(draft(), PAGES)                                      # spacing differs: still found
    assert not is_grounded(draft(name="Gram Panchayat Office", quote="Gram Panchayat Office Wadgaon"), PAGES)
    assert not is_grounded(draft(page=3), PAGES)                            # real quote, wrong page
    assert not is_grounded(draft(name="Town Hall"), PAGES)                  # name not in its quote
    assert not is_grounded(draft(page=9), PAGES)


def test_only_pages_with_shelter_words_are_sent(india):
    assert batches(PAGES, india["shelter_words"]) == [[2]]
    assert batches(["राहत शिविर सूची", "x" * 20, "निवारा केंद्र"], india["shelter_words"], max_chars=10) == [[1], [3]]


def test_the_model_cannot_add_a_shelter_the_plan_does_not_name(india):
    invented = {"name": "Collector Office", "place_type": "shelter", "page": 2, "quote": "Collector Office"}
    model = ScriptedModel([
        ("tool", "ShelterDrafts", {"shelters": [draft().model_dump(), invented]}),
        "done",
    ])
    result = extract_shelters(PAGES, india["shelter_words"], model)
    assert [d.name for d in result.drafts] == ["Z.P. School"]
    assert (result.dropped, result.pages_sent, result.pages_with_text) == (1, 1, 3)


class FakeGeocoder:
    def __init__(self, answers: dict[str, list[tuple[float, float]]]):
        self.answers = answers

    def search(self, name, country_code, language="en"):
        return [PlaceCandidate(name, lat, lon, AdminArea(country_code, None, None), "fake")
                for lat, lon in self.answers.get(name, [])]


def test_locations_must_fall_inside_the_district_and_say_how_precise_they_are():
    centre = (20.7, 78.6)
    far_namesake = FakeGeocoder({"Z.P. School, Wadgaon": [(28.6, 77.2)], "Wadgaon, Wardha": [(20.75, 78.62)]})
    assert locate(draft(), "Wardha", centre, "in", far_namesake, 80) == (20.75, 78.62, "village")
    assert locate(draft(), "Wardha", centre, "in", FakeGeocoder({}), 80) is None
    assert locate(draft(), "Wardha", None, "in", far_namesake, 80) is None


# --- review ---------------------------------------------------------------------------------

def candidate(**kw) -> dict:
    base = {"name": "Z.P. School", "type": "shelter", "lat": "20.75", "lon": "78.62", "hazards": "flood",
            "district": "Wardha", "source": "DDMP 2025, p.2: https://x/plan.pdf", "page": "2",
            "quote": "Z.P. School Wadgaon", "plan_sha256": "abc"}
    return {**base, **kw}


def test_rerunning_extraction_never_overwrites_a_reviewers_decision(tmp_path):
    path = tmp_path / "candidates.csv"
    assert add_candidates(path, [candidate()]) == 1
    rows = read_csv(path)
    rows[0]["status"], rows[0]["hazards"] = "rejected", "cyclone"
    from weatherwise.shelter_data.review import CANDIDATE_FIELDS, write_csv
    write_csv(path, rows, CANDIDATE_FIELDS)
    assert add_candidates(path, [candidate(), candidate(name="Community Hall")]) == 1
    rows = read_csv(path)
    assert [(r["name"], r["status"], r["hazards"]) for r in rows] == [
        ("Z.P. School", "rejected", "cyclone"), ("Community Hall", "pending", "flood")]


def test_only_approved_complete_rows_reach_the_shelter_list(tmp_path):
    from weatherwise.shelter_data.review import CANDIDATE_FIELDS, write_csv
    candidates, shelters = tmp_path / "c.csv", tmp_path / "shelters_xx.csv"
    write_csv(candidates, [
        candidate(status="approved"),
        candidate(status="approved", name="No Location", lat="", lon=""),
        candidate(status="approved", name="Bad Hazard", hazards="tsunami"),
        candidate(status="pending", name="Not Reviewed"),
        candidate(status="rejected", name="Rejected"),
    ], CANDIDATE_FIELDS)
    with pytest.raises(ValueError, match="checked_by"):
        approve(candidates, shelters, date(2026, 11, 1), " ", 30)
    result = approve(candidates, shelters, date(2026, 11, 1), "Prashant", 30)
    assert result.added == ["Z.P. School"]
    assert {name for name, _ in result.not_ready} == {"No Location", "Bad Hazard"}
    assert approve(candidates, shelters, date(2026, 11, 1), "Prashant", 30).already_listed == ["Z.P. School"]

    listed = load_shelters("xx", root=tmp_path)    # the router's own loader accepts the rows
    assert [(s.name, s.hazards, s.recheck_due) for s in listed] == [("Z.P. School", ("flood",), date(2026, 12, 1))]
