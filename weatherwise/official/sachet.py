"""Official warnings for a point, from SACHET (sachet.ndma.gov.in), the National Disaster
Management Authority's alert platform where IMD and every state disaster authority publish
warnings in the Common Alerting Protocol.

We ask SACHET the same question its own website asks for a location (the alerts whose area
covers the point, within a radius) and keep only the text: SACHET also sends each area's map
shape, which can be over 1 MB. Messages come in the issuer's language; SACHET's translation
service gives them in the person's language. (It translates the alert it is given by id, so it is
used for messages only; event names are short and translated by the website's text files.)

Rules:
- If SACHET cannot be reached, the answer is "unavailable", never "no warnings".
- Expired alerts are dropped.
- We identify ourselves honestly (USER_AGENT) and cache per area, so we ask rarely.
"""

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from weatherwise.cache import Cache, cached
from weatherwise.https import urlopen
from weatherwise.places.geocoding import USER_AGENT

SACHET = "https://sachet.ndma.gov.in/cap_public_website"
SOURCE = "SACHET, National Disaster Management Authority (sachet.ndma.gov.in)"
IST = timezone(timedelta(hours=5, minutes=30))
POINT_ROUNDING = 2  # decimals: ~1 km, enough for a 20 km search, kinder to the person and the cache

# SACHET's colour code (IMD's), most serious first.
LEVELS = ("red", "orange", "yellow", "green")
LEVEL_FOR_WORD = {"WARNING": "red", "ALERT": "orange", "WATCH": "yellow", "ADVISORY": "green"}

# Official alerts that mean flooding, so they decide the flood guide (red: urgent, orange: prepare).
FLOOD_WORDS = ("flood", "rain", "cyclone", "depression", "storm surge", "inundation", "cloudburst")


@dataclass(frozen=True)
class OfficialAlert:
    id: str
    event: str
    level: str            # red / orange / yellow / green
    level_word: str       # as issued: WARNING / ALERT / WATCH / ADVISORY
    source: str           # who issued it, e.g. "Telangana SDMA", "IMD Ranchi"
    area: str
    starts: str           # ISO 8601, IST
    ends: str
    language: str         # language of the original message
    message: str
    translations: dict[str, str] = field(default_factory=dict)  # lang -> message

    @property
    def flood_related(self) -> bool:
        return any(w in self.event.lower() for w in FLOOD_WORDS)


def _when(text: str) -> datetime:
    """SACHET writes times like "Sun Nov 01 08:31:00 IST 2026"."""
    return datetime.strptime(text.replace(" IST ", " "), "%a %b %d %H:%M:%S %Y").replace(tzinfo=IST)


def parse_alert(raw: dict) -> OfficialAlert:
    word = str(raw.get("severity") or "").upper()
    colour = str(raw.get("severity_color") or "").lower()
    return OfficialAlert(
        id=str(raw["identifier"]),
        event=str(raw.get("disaster_type") or "").strip(),
        level=colour if colour in LEVELS else LEVEL_FOR_WORD.get(word, "yellow"),
        level_word=word,
        source=str(raw.get("alert_source") or "").strip(),
        area=str(raw.get("area_description") or "").strip(),
        starts=_when(raw["effective_start_time"]).isoformat(),
        ends=_when(raw["effective_end_time"]).isoformat(),
        language=str(raw.get("actual_lang") or "en").lower(),
        message=str(raw.get("warning_message") or "").strip(),
    )


def _post_json(path: str, params: dict, timeout: float = 30) -> dict:
    url = f"{SACHET}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=b"", method="POST",
                                 headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read(), strict=False)


def _without_repeats(alerts: list[dict]) -> list[dict]:
    """Most serious first; the same warning issued for overlapping areas shown once (the one in
    force longest)."""
    best: dict[tuple, dict] = {}
    for a in alerts:
        key = (a["event"], a["level"], a["source"], a["message"])
        if key not in best or a["ends"] > best[key]["ends"]:
            best[key] = a
    return sorted(best.values(), key=lambda a: LEVELS.index(a["level"]))


def most_serious(alerts: list[dict], flood_only: bool = False) -> str | None:
    """The highest official colour among (flood-related) alerts, or None."""
    levels = [a["level"] for a in alerts if not flood_only or a["flood_related"]]
    return next((lv for lv in LEVELS if lv in levels), None)


@dataclass
class SachetAlerts:
    cache: Cache
    post: Callable[[str, dict], dict] = _post_json
    now: Callable[[], datetime] = lambda: datetime.now(IST)
    radius_km: int = 20
    languages: tuple[str, ...] = ("en", "hi", "mr")

    def for_point(self, lat: float, lon: float) -> dict:
        """{"status": "ok" | "unavailable", "alerts": [...most serious first], "source": ...}"""
        lat, lon = round(lat, POINT_ROUNDING), round(lon, POINT_ROUNDING)
        try:
            raw = cached(self.cache, "official_alerts", f"{lat}:{lon}:{self.radius_km}",
                         lambda: self.post("FetchLocationWiseAlerts",
                                           {"lat": lat, "long": lon, "radius": self.radius_km}).get("alerts") or [])
        except Exception:  # unreachable is reported as such, never read as "no warnings"
            return {"status": "unavailable", "alerts": [], "source": SOURCE}
        now = self.now()
        alerts = []
        for item in raw:
            try:
                alert = parse_alert(item)
            except (KeyError, ValueError):
                continue  # one malformed alert must not hide the others
            if datetime.fromisoformat(alert.ends) < now:
                continue
            alert.translations.update(self._translations(alert))
            alerts.append({**asdict(alert), "flood_related": alert.flood_related})
        return {"status": "ok", "alerts": _without_repeats(alerts), "source": SOURCE}

    def _translations(self, alert: OfficialAlert) -> dict[str, str]:
        """The message in each website language, by SACHET's translation service.
        A failed translation is simply left out: the original is always shown."""
        out = {alert.language: alert.message}
        for lang in self.languages:
            if lang == alert.language:
                continue
            try:
                out[lang] = cached(self.cache, "official_translation", f"{alert.id}:{lang}",
                                   lambda lang=lang: self._translate(alert, alert.message, lang))
            except Exception:  # noqa: S112 - the original message is still shown
                continue
        return out

    def _translate(self, alert: OfficialAlert, text: str, lang: str) -> str:
        if not text:
            return text
        reply = self.post("FetchTextTranslation", {"text": text, "sourceLang": alert.language,
                                                   "targetLang": lang, "identifier": alert.id})
        if reply.get("response") != "Success" or not reply.get("body"):
            raise ValueError("translation not available")
        return str(reply["body"]).strip()
