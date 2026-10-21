# tests/test_supervisor.py
import json
import socket
from datetime import datetime
from pathlib import Path

import pytest

from sahra.audit import AuditLog
from sahra.gate import ApprovalGate
from sahra.hitl import ApprovalQueue
from sahra.supervisor import DayTimeline, HourlyStep, run_day
from sahra.types import InterventionKind, PopulationGroup, RiskLevel

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "dubai_hourly_2026-07-01.json"
ZONE = "dubai-2026-07-01"
APPROVER = "coordinator@dxbops"


def run_archived_day(tmp_path, queue=None):
    audit = AuditLog(tmp_path / "audit.jsonl")
    timeline = run_day(ZONE, PopulationGroup.SCHOOL, FIXTURE, ApprovalGate(), audit, queue)
    return timeline, audit


def write_extreme_fixture(path):
    """A synthetic three-hour day whose midday hour bands extreme.

    The archived ERA5 day peaks at 31.4 C and never reaches the 32 C extreme
    band, so the escalation path needs its own fixture to be exercised at all.
    """
    def hour(h, air, solar, direct):
        return {
            "time": f"2026-07-01T{h}:00:00+04:00", "air_temp_c": air,
            "humidity_pct": 45.0, "dew_point_c": 24.0, "wind_ms": 3.0,
            "global_radiation_wm2": solar, "direct_radiation_wm2": direct,
            "diffuse_radiation_wm2": solar - direct,
        }

    payload = {
        "meta": {
            "zone_id": "synthetic-extreme", "latitude": 25.202108,
            "longitude": 55.302376, "timezone": "Asia/Dubai",
            "note": "synthetic fixture written by the test, not observed weather",
        },
        "hours": [hour("11", 37.0, 800.0, 560.0),
                  hour("12", 38.5, 900.0, 620.0),
                  hour("13", 37.0, 820.0, 570.0)],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_one_day_is_24_ordered_hourly_steps(tmp_path):
    timeline, _ = run_archived_day(tmp_path)
    assert isinstance(timeline, DayTimeline)
    assert timeline.zone_id == ZONE
    assert timeline.group is PopulationGroup.SCHOOL
    assert timeline.date == "2026-07-01"
    assert len(timeline.steps) == 24
    assert all(isinstance(step, HourlyStep) for step in timeline.steps)
    hours = [step.at for step in timeline.steps]
    assert hours[0] == datetime.fromisoformat("2026-07-01T00:00:00+04:00")
    assert hours[-1] == datetime.fromisoformat("2026-07-01T23:00:00+04:00")
    assert hours == sorted(hours)
    assert all(step.statuses for step in timeline.steps)


def test_the_day_reads_as_a_rising_curve_and_peaks_in_the_midday_window(tmp_path):
    timeline, _ = run_archived_day(tmp_path)
    levels = [step.level for step in timeline.steps]
    assert levels[0] is RiskLevel.MODERATE
    assert RiskLevel.LOW in levels
    assert RiskLevel.HIGH in levels
    assert RiskLevel.EXTREME not in levels
    assert timeline.peak_wbgt_c == pytest.approx(31.4, abs=0.05)
    assert timeline.peak_at == datetime.fromisoformat("2026-07-01T11:00:00+04:00")
    assert max(step.wbgt_c for step in timeline.steps) == timeline.peak_wbgt_c
    assert timeline.pending_ids == []

    first = timeline.steps[0]
    assert first.dispatched_kinds == [InterventionKind.SHIFT_ACTIVITY, InterventionKind.ADVISE]
    assert first.active_kinds == []
    second = timeline.steps[1]
    assert second.dispatched_kinds == []
    assert second.active_kinds == [InterventionKind.SHIFT_ACTIVITY, InterventionKind.ADVISE]

    high = timeline.steps[9]
    assert high.level is RiskLevel.HIGH
    assert high.dispatched_kinds == [InterventionKind.ACTIVATE_COOLING]
    assert high.active_kinds == [InterventionKind.SHIFT_ACTIVITY, InterventionKind.ADVISE]
    assert all(not step.dispatched_kinds for step in timeline.steps[10:])

    dispatched = [kind for step in timeline.steps for kind in step.dispatched_kinds]
    assert sorted(dispatched) == sorted(set(dispatched))


def test_every_action_of_every_cycle_is_in_the_audit_file(tmp_path):
    timeline, audit = run_archived_day(tmp_path)
    records = audit.read_all()
    total = sum(len(step.statuses) for step in timeline.steps)
    assert total == 57
    assert len(records) == total
    assert [r.status for r in records] == [s for step in timeline.steps for s in step.statuses]
    assert sorted(r.intervention.kind for r in records) == sorted(
        kind for step in timeline.steps
        for kind in step.dispatched_kinds + step.active_kinds)


def test_a_refused_escalation_becomes_a_pending_request_that_an_approval_executes(tmp_path):
    path = write_extreme_fixture(tmp_path / "extreme.json")
    audit = AuditLog(tmp_path / "audit.jsonl")
    queue = ApprovalQueue(audit)
    timeline = run_day("synthetic-extreme", PopulationGroup.OUTDOOR_WORKER, path,
                       ApprovalGate(), audit, queue)

    assert [step.level for step in timeline.steps] == [RiskLevel.HIGH, RiskLevel.EXTREME, RiskLevel.HIGH]
    extreme = timeline.steps[1]
    assert extreme.dispatched_kinds == [InterventionKind.ESCALATE]
    assert extreme.statuses == ["refused", "executed", "executed", "executed"]

    assert len(timeline.pending_ids) == 1
    pending = queue.get(timeline.pending_ids[0])
    assert pending.status == "pending"
    assert pending.intervention.kind is InterventionKind.ESCALATE
    refusals = [r for r in audit.read_all() if r.status == "refused"]
    assert len(refusals) == 1
    assert refusals[0].approved_by is None

    record = queue.decide(timeline.pending_ids[0], APPROVER, approve=True)
    assert record.status == "executed"
    assert record.approved_by == APPROVER
    assert record.intervention.kind is InterventionKind.ESCALATE
    written = audit.read_all()
    assert len(written) == 11
    assert written[-1].status == "executed"
    assert written[-1].approved_by == APPROVER
    assert queue.pending() == []


def test_the_day_runs_offline(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("the supervisor must not touch the network")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    timeline, _ = run_archived_day(tmp_path)
    assert len(timeline.steps) == 24
    assert timeline.peak_at == datetime.fromisoformat("2026-07-01T11:00:00+04:00")
