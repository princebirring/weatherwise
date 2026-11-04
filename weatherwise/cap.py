"""Turns a HazardDetection into a CAP 1.2 alert (OASIS standard), so our warnings can feed
existing systems such as SACHET instead of competing with them.

We are not an official warning service, so the sender name says so and the
default status is "Exercise"; a deployment that is authorised to publish can pass "Actual".
"""

import uuid
from datetime import datetime, time, timedelta
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from weatherwise.risk.models import Hazard, HazardDetection

CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"
SENDER = "weatherwise@open-source"
SENDER_NAME = "WeatherWise (open source; not an official warning service; follow IMD)"

EVENT_NAMES = {
    Hazard.HEAT_WAVE: "Heat wave",
    Hazard.WORK_HEAT: "Heat too high for outdoor work",
    Hazard.EXCESS_HEAT: "Excess heat",
    Hazard.HEAVY_RAIN: "Heavy rain",
    Hazard.UNUSUAL_RAIN: "Rain unusual for this place",
    Hazard.DRY_SPELL: "Dry spell",
    Hazard.SOWING_RISK: "Dry soil at sowing time",
    Hazard.RIVER_FLOOD: "River flood risk",
}
SEVERITY = {
    "extremely_heavy": "Severe", "severe": "Severe", "very_heavy": "Moderate",
    "heat_wave": "Moderate", "heatwave": "Moderate", "danger": "Severe", "take_care": "Minor",
    "heavy": "Minor", "unusual": "Moderate",
    "above_flood_level": "Moderate", "dry_spell": "Moderate", "sow_or_wait": "Minor",
}
CATEGORY = {Hazard.DRY_SPELL: "Env", Hazard.SOWING_RISK: "Env"}  # everything else is "Met"


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def detection_to_cap(
    d: HazardDetection,
    area_desc: str,
    lat: float,
    lon: float,
    timezone: str,
    headline: str,
    instruction: str,
    sent: datetime | None = None,
    status: str = "Exercise",
    radius_km: float = 15.0,
    language: str = "en",
) -> str:
    tz = ZoneInfo(timezone)
    sent = (sent or datetime.now(tz)).replace(microsecond=0)
    onset = datetime.combine(d.first_day, time(0, 0), tz)
    expires = datetime.combine(d.last_day + timedelta(days=1), time(0, 0), tz)

    ET.register_namespace("", CAP_NS)
    alert = ET.Element(f"{{{CAP_NS}}}alert")

    def add(parent, tag, text):
        el = ET.SubElement(parent, f"{{{CAP_NS}}}{tag}")
        el.text = str(text)
        return el

    add(alert, "identifier", f"cra-{uuid.uuid4()}")
    add(alert, "sender", SENDER)
    add(alert, "sent", _iso(sent))
    add(alert, "status", status)
    add(alert, "msgType", "Alert")
    add(alert, "scope", "Public")

    info = ET.SubElement(alert, f"{{{CAP_NS}}}info")
    add(info, "language", language)
    add(info, "category", CATEGORY.get(d.hazard, "Met"))
    add(info, "event", EVENT_NAMES[d.hazard])
    add(info, "responseType", "Prepare")
    add(info, "urgency", "Immediate" if d.days_ahead <= 0 else "Expected" if d.days_ahead <= 2 else "Future")
    add(info, "severity", SEVERITY.get(d.severity, "Unknown"))
    add(info, "certainty", "Likely" if d.agreement >= 0.5 else "Possible")
    add(info, "effective", _iso(sent))
    add(info, "onset", _iso(onset))
    add(info, "expires", _iso(expires))
    add(info, "senderName", SENDER_NAME)
    add(info, "headline", headline)
    add(info, "description",
        f"{EVENT_NAMES[d.hazard]} ({d.severity}) expected {d.first_day} to {d.last_day}; "
        f"{d.agreement:.0%} of forecast runs agree.")
    add(info, "instruction", instruction)
    for name, value in (("forecast_run_agreement", d.agreement), ("days_ahead", d.days_ahead),
                        ("rule", d.evidence.get("rule", "official definition"))):
        p = ET.SubElement(info, f"{{{CAP_NS}}}parameter")
        add(p, "valueName", name)
        add(p, "value", value)

    area = ET.SubElement(info, f"{{{CAP_NS}}}area")
    add(area, "areaDesc", area_desc)
    add(area, "circle", f"{lat:.4f},{lon:.4f} {radius_km}")
    return ET.tostring(alert, encoding="unicode", xml_declaration=True)
