from datetime import datetime, timezone
from sahra.channels.notify import render_advisory, render_operator_view
from sahra.types import (
    ActionRecord, CycleResult, HeatState, Intervention, InterventionKind,
    PopulationGroup, RiskAssessment, RiskLevel,
)

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def result():
    st = HeatState(zone_id="school-dxb-001", at=AT, air_temp_c=44.0, humidity_pct=70.0,
                   wbgt_c=31.0, lst_c=48.2, source_tier="site")
    ra = RiskAssessment(zone_id="school-dxb-001", at=AT, group=PopulationGroup.SCHOOL,
                        wbgt_c=31.0, score=0.5, level=RiskLevel.HIGH)
    iv = Intervention(kind=InterventionKind.SHIFT_ACTIVITY,
                      reason="WBGT 31.0C exceeds the 28C occupational threshold",
                      expected_risk_reduction=0.35)
    ar = ActionRecord(action_id="a1", intervention=iv, status="executed", at=AT,
                      reason_trace=["wbgt=31.0", "threshold=28.0"])
    return CycleResult(state=st, assessment=ra, interventions=[iv], actions=[ar])


def test_advisory_is_english_and_names_the_zone_and_level():
    text = render_advisory(result())
    assert "school-dxb-001" in text
    assert "high" in text.lower()
    assert "shift_activity" in text


def test_advisory_carries_no_pii():
    text = render_advisory(result()).lower()
    for banned in ("student_name", "worker_name", "emirates_id", "phone", "email"):
        assert banned not in text


def test_operator_view_reports_every_action_with_its_status():
    text = render_operator_view(result())
    assert "a1" in text and "executed" in text and "wbgt=31.0" in text
