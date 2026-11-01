"""Builds the verified shelter list (data/shelters_<iso>.csv) from official district disaster
plans, for any country with a [shelter_sources] section in its rules file.

    districts   every district + its official website (OpenStreetMap + Wikidata)
    finder      the district's disaster management plan on its website
    extraction  shelters named in the plan (Claude on Bedrock, via Strands), each with page + quote
    review      drafts -> human approval -> data/shelters_<iso>.csv

Runs ahead of time (scripts/shelter_data.py). Nothing here runs when a person asks for a shelter:
weatherwise/shelters.py only reads the finished CSV.
"""

from weatherwise.rules import ConfigError


def shelter_sources(rules: dict) -> dict:
    """The country's [shelter_sources] section, or a clear error if the country has none yet."""
    section = rules.get("shelter_sources")
    keys = ("osm_country", "district_admin_level", "domain_suffixes", "search_paths", "disaster_words", "plan_words",
            "not_plan_words", "district_words", "shelter_words")
    if not section or any(k not in section for k in keys):
        raise ConfigError(f"[shelter_sources] needs: {', '.join(keys)}")
    return section
