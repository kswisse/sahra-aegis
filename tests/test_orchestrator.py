from datetime import datetime, timezone

from sahra.audit import AuditLog
from sahra.gate import ApprovalGate
from sahra.orchestrator import run_cycle
from sahra.types import (
    InterventionKind,
    PopulationGroup,
    RiskLevel,
    SiteReading,
    WeatherReading,
)

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def run(tmp_path, wbgt, approved_by=None):
    return run_cycle(
        zone_id="school-dxb-001", group=PopulationGroup.SCHOOL, at=AT,
        satellite=None,
        weather=WeatherReading(air_temp_c=44.0, humidity_pct=70.0),
        site=SiteReading(wbgt_c=wbgt),
        gate=ApprovalGate(), audit=AuditLog(tmp_path / "audit.jsonl"),
        approved_by=approved_by,
    )


def test_calm_day_produces_advisory_only(tmp_path):
    r = run(tmp_path, 25.0)
    assert r.assessment.level is RiskLevel.LOW
    assert [a.status for a in r.actions] == ["executed"]


def test_hazardous_day_executes_every_reversible_action(tmp_path):
    r = run(tmp_path, 31.0)
    assert r.assessment.level is RiskLevel.HIGH
    assert all(a.status in ("executed", "refused") for a in r.actions)
    assert any(
        a.intervention.kind is InterventionKind.SHIFT_ACTIVITY for a in r.actions
    )


def test_extreme_day_without_approval_refuses_escalation_and_logs_it(tmp_path):
    r = run(tmp_path, 33.5)
    refused = [a for a in r.actions if a.status == "refused"]
    assert len(refused) == 1
    assert refused[0].intervention.consequential is True
    assert len(AuditLog(tmp_path / "audit.jsonl").read_all()) == len(r.actions)


def test_extreme_day_with_approval_executes_escalation(tmp_path):
    r = run(tmp_path, 33.5, approved_by="coordinator@schooldxb")
    assert all(a.status == "executed" for a in r.actions)
    assert any(a.approved_by for a in r.actions)


def test_every_action_has_a_reason_trace(tmp_path):
    r = run(tmp_path, 33.5)
    assert r.actions and all(a.reason_trace for a in r.actions)
