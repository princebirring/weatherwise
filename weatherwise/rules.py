"""Rules and data the system cannot fetch from any API (plan §8.9).

    rules/global.toml            our own rules, used in every country
    rules/countries/<iso>.toml   official definitions and national policy (e.g. in.toml: IMD)
    rules/languages/<code>.toml  our safety text per language (safe messages, footer, unsafe phrases)
    data/shelters_<iso>.csv      verified shelters (data, not config)
    data/river_catchments_<iso>.toml  pilot upstream rain points (temporary, labelled)

No state level: nothing here varies by state. Time zone comes from each place's coordinates
and language from the person. Only the MCP server reads these files; agents receive them
through the message_policy tool.
"""

import hashlib
import tomllib
from datetime import date
from functools import lru_cache
from pathlib import Path

from weatherwise.risk.models import RainPoint

ROOT = Path(__file__).resolve().parent.parent
RULES_ROOT = ROOT / "rules"
DATA_ROOT = ROOT / "data"

# Every key the engine needs, checked at load so a gap fails at startup, never at 6 AM.
REQUIRED_KEYS = {
    "country": ["name", "default_languages"],
    "terrain": ["coast_max_km", "hills_min_elevation_m"],
    "helplines": ["emergency", "disaster"],
    "heat": ["rule", "min_consecutive_days", "min_agreement", "first_warning_lead_days"],
    "humid_heat": ["apparent_tmax_danger", "min_consecutive_days", "min_agreement"],
    "excess_heat": ["reference_first_year", "reference_last_year", "heat_percentile",
                    "severe_percentile", "min_agreement", "min_consecutive_days"],
    "heavy_rain": ["heavy", "very_heavy", "extremely_heavy", "min_agreement"],
    "dry_spell": ["dry_day_max_mm", "min_dry_days", "min_agreement", "soil_moisture_dry"],
    "sowing": ["forecast_days", "max_total_rain_mm", "min_agreement"],
    "river_flood": ["flood_level_return_period_years", "history_first_year", "min_agreement"],
    "river_exposure": ["min_flood_flow_m3s", "screen_years"],
    "flood_guide": ["prepare_within_days", "urgent_within_days", "prepare_rain_categories", "stay_on_quiet_days",
                    "urgent_rain_category"],
    "seasons": ["rainfed_crop_seasons", "sowing_windows"],
    "messages": ["max_chars_reply", "max_chars_urgent", "no_links_in_floods", "required_numbers"],
    "delivery": ["send_from_hour", "send_until_hour", "max_warnings_per_month",
                 "max_messages_per_event"],
}


class ConfigError(ValueError):
    """Rules are missing or inconsistent."""


class UnsupportedCountry(ValueError):
    """The place is in a country we have no rules for."""

    def __init__(self, message: str, country_code: str = ""):
        super().__init__(message)
        self.country_code = country_code


def _read(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def _merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


def validate_rules(rules: dict, country: str) -> None:
    missing = [f"[{s}] {k}" for s, keys in REQUIRED_KEYS.items() for k in keys
               if k not in rules.get(s, {})]
    if missing:
        raise ConfigError(f"rules for {country!r} are missing: {', '.join(missing)}")


def supported_countries(root: Path = RULES_ROOT) -> list[str]:
    return sorted(p.stem for p in (root / "countries").glob("*.toml"))


def country_for(country_code: str, root: Path = RULES_ROOT) -> str:
    """The rules key for an ISO country code from reverse geocoding (e.g. "in")."""
    code = (country_code or "").lower()
    if code not in supported_countries(root):
        raise UnsupportedCountry(f"no rules for country {country_code!r}", code)
    return code


def load_rules(country: str, root: Path = RULES_ROOT, validate: bool = True) -> dict:
    """Global rules, overridden by the country's file."""
    path = root / "countries" / f"{country}.toml"
    if not path.exists():
        raise UnsupportedCountry(f"no rules for country {country!r}")
    merged = _read(root / "global.toml") if (root / "global.toml").exists() else {}
    _merge(merged, _read(path))
    if validate:
        validate_rules(merged, country)
    return merged


def supported_languages(root: Path = RULES_ROOT) -> list[str]:
    return sorted(p.stem for p in (root / "languages").glob("*.toml"))


def load_language(code: str, root: Path = RULES_ROOT) -> dict:
    path = root / "languages" / f"{code}.toml"
    return _read(path) if path.exists() else {}


def _verified(text: str | None) -> str | None:
    return text if text and not text.startswith("TODO") else None


def _verified_guidance(value):
    """A guidance value (text, or a list of texts or {who, what} items) with no TODO anywhere."""
    texts = [value] if isinstance(value, str) else [
        t for item in value for t in (item.values() if isinstance(item, dict) else [item])]
    return value if texts and all(_verified(t) for t in texts) else None


def message_policy(country: str, root: Path = RULES_ROOT) -> dict:
    """Everything an agent needs to check and send messages for a country, in one JSON-ready
    dict (served by the MCP message_policy tool). Unsafe phrases are the union of all
    languages; safe messages, footers and website guidance fall back to English where not yet verified."""
    rules = load_rules(country, root)
    languages = {code: load_language(code, root) for code in supported_languages(root)}
    english = languages.get("en", {})

    def text(lang: dict, section: str, key: str) -> str | None:
        return _verified(lang.get(section, {}).get(key)) or _verified(english.get(section, {}).get(key))

    def union(key: str) -> list[str]:
        return sorted({p for lang in languages.values() for p in lang.get("unsafe_phrases", {}).get(key, [])})

    return {
        "country": country,
        "helplines": rules["helplines"],
        "default_languages": rules["country"]["default_languages"],
        "messages": {
            **{k: rules["messages"][k] for k in ("max_chars_reply", "max_chars_urgent",
                                                  "no_links_in_floods", "required_numbers")},
            "high_ground_phrases": union("high_ground"),
            "slope_safety_words": union("slope_safety_words"),
            "never_say": union("never_say"),
        },
        "delivery": rules["delivery"],
        "safe_messages": {
            code: {kind: text(lang, "safe_messages", kind) for kind in ("general", "heat", "flood")}
            for code, lang in languages.items()
        },
        "footer": {code: text(lang, "footer", "text") for code, lang in languages.items()},
        "guidance": {
            code: {key: _verified_guidance(lang.get("guidance", {}).get(key, "TODO")) or english_value
                   for key, english_value in english.get("guidance", {}).items()}
            for code, lang in languages.items()
        },
        "rules_version": rules_version(),
    }


@lru_cache(maxsize=1)
def rules_version() -> str:
    """Short hash of every rules and data file, so out-of-step deployments are detectable."""
    digest = hashlib.sha256()
    for root in (RULES_ROOT, DATA_ROOT):
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def load_river_catchments(country: str, root: Path = DATA_ROOT) -> list[dict]:
    """Pilot upstream-rain catchments (labelled pilot data until river-network data)."""
    path = root / f"river_catchments_{country}.toml"
    if not path.exists():
        return []
    return [
        {**c, "upstream_rain_points": tuple(RainPoint(p["name"], p["lat"], p["lon"])
                                            for p in c.get("upstream_rain_point", []))}
        for c in _read(path).get("catchment", [])
    ]


def in_season(day: date, window: list[str]) -> bool:
    """True if day falls in a ["MM-DD", "MM-DD"] window (may wrap past new year)."""
    start, end = window
    md = day.strftime("%m-%d")
    return start <= md <= end if start <= end else md >= start or md <= end
