"""The scheduled warning Graph end to end with a scripted model (plan §5.1, §5.2, §16)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fake_model import ScriptedModel

from weatherwise.agents.delivery import MemoryLedger, MemoryOutbox, SentRecord
from weatherwise.agents.warning_pipeline import RecipientGroupRun, WarningPipeline
from weatherwise.rules import message_policy

IST = ZoneInfo("Asia/Kolkata")
POLICY = message_policy("in")
MORNING = datetime(2026, 4, 22, 7, 15, tzinfo=IST)
NIGHT = datetime(2026, 4, 22, 23, 0, tzinfo=IST)
GROUP = RecipientGroupRun("Akola", 20.7, 77.0, "en", "cotton", "well",
                          ("farmer-1", "farmer-2"))

HEAT = {"issue_date": "2026-04-22", "place": {"name": "Akola"},
        "detections": [{"hazard": "excess_heat", "severity": "severe", "first_day": "2026-04-25",
                        "last_day": "2026-04-27", "days_ahead": 3, "agreement": 0.83,
                        "evidence": {"t95": 35.0}}],
        "flood_guide": {"mode": None, "reasons": []}, "tmax_c": 44.0}
QUIET = {"issue_date": "2026-04-22", "place": {"name": "Akola"}, "detections": [],
         "flood_guide": {"mode": None, "reasons": []}}
URGENT = {"issue_date": "2026-07-25", "place": {"name": "Kolhapur"}, "detections": [],
          "flood_guide": {"mode": "urgent", "reasons": ["official red alert"]}}

SAFE_HEAT = "Severe heat likely Sat-Mon, around 44 °C (83% of forecasts agree). Work before 10 am; water your cattle often. Heatstroke: call 108."
UNSAFE = "Severe heat, 48 °C. Stay inside."
SAFE_URGENT = "Move to a safe place now, away from rivers and away from hill slopes. Call 112 / 1077."


def pipeline(outlook, script):
    ledger, outbox, model = MemoryLedger(), MemoryOutbox(), ScriptedModel(script)
    p = WarningPipeline(lambda lat, lon, name: outlook, model, ledger, outbox, POLICY, with_tone_check=False)
    return p, ledger, outbox, model


def test_quiet_day_costs_no_ai_and_sends_nothing():
    p, _, outbox, model = pipeline(QUIET, [])
    rec = p.run(GROUP, MORNING)
    assert rec.hazard_kind is None and model.calls == 0 and outbox.messages == []


def test_heat_warning_written_checked_footed_and_sent_to_group():
    p, ledger, outbox, _ = pipeline(HEAT, [SAFE_HEAT])
    rec = p.run(GROUP, MORNING)
    assert rec.hazard_kind == "heat_dry" and not rec.used_fallback
    assert [m["to"] for m in outbox.messages] == ["farmer-1", "farmer-2"]
    assert outbox.messages[0]["text"].startswith(SAFE_HEAT)
    assert "Not an official warning service" in outbox.messages[0]["text"]
    assert len(ledger.records) == 2


def test_unsafe_drafts_end_in_the_safe_fallback():
    p, _, outbox, _ = pipeline(HEAT, [UNSAFE, UNSAFE, UNSAFE])
    rec = p.run(GROUP, MORNING)
    assert rec.used_fallback
    assert outbox.messages[0]["text"].startswith("Heat warning for your area")


def test_quiet_hours_defer_normal_warnings():
    p, _, outbox, _ = pipeline(HEAT, [SAFE_HEAT])
    rec = p.run(GROUP, NIGHT)
    assert set(rec.deliveries.values()) == {"defer"} and outbox.messages == []


def test_monthly_cap_skips_but_urgent_still_goes_out_at_night():
    p, ledger, outbox, _ = pipeline(URGENT, [SAFE_URGENT])
    for i in range(4):
        ledger.add(SentRecord("farmer-1", f"heat:{i}", MORNING, urgent=False))
    rec = p.run(GROUP, NIGHT)
    assert rec.hazard_kind == "flood"
    assert rec.deliveries == {"farmer-1": "send", "farmer-2": "send"}
    assert outbox.messages[0]["urgent"] is True


def test_monthly_cap_applies_to_normal_warnings():
    p, ledger, _, _ = pipeline(HEAT, [SAFE_HEAT])
    for i in range(4):
        ledger.add(SentRecord("farmer-1", f"heat:{i}", MORNING, urgent=False))
    rec = p.run(GROUP, MORNING)
    assert rec.deliveries == {"farmer-1": "skip", "farmer-2": "send"}


def test_rules_version_mismatch_is_flagged():
    stale = {**HEAT, "rules_version": "000000000000"}
    p, _, _, _ = pipeline(stale, [SAFE_HEAT])
    assert p.run(GROUP, MORNING).rules_version_mismatch


def test_matching_rules_version_is_not_flagged():
    p, _, _, _ = pipeline({**HEAT, "rules_version": POLICY["rules_version"]}, [SAFE_HEAT])
    assert not p.run(GROUP, MORNING).rules_version_mismatch
