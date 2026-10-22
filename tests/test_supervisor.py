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

    A controlled vector for the refusal -> pending request -> approval path:
    three hours, one band change, and no dependence on which archived days
    happen to escalate. Every row here is a test vector, not observed weather.
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
            "dataset": "synthetic test vector",
            "note": "synthetic fixture written by the test, not observed weather",
        },
        "hours": [hour("11", 34.0, 800.0, 560.0),
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
    timeline, audit = run_archived_day(tmp_path)
    levels = [step.level for step in timeline.steps]
    assert levels == (
        [RiskLevel.MODERATE] * 5
        + [RiskLevel.LOW] * 2
        + [RiskLevel.MODERATE] * 2
        + [RiskLevel.HIGH] * 11
        + [RiskLevel.MODERATE] * 4
    )
    assert levels[0] is RiskLevel.MODERATE
    assert levels[9] is RiskLevel.HIGH
    assert levels[20] is RiskLevel.MODERATE
    assert levels[-1] is RiskLevel.MODERATE
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

    logged = [r.intervention.kind for r in audit.read_all() if r.at == high.at]
    assert logged == [InterventionKind.SHIFT_ACTIVITY, InterventionKind.ACTIVATE_COOLING,
                      InterventionKind.ADVISE]
    assert list(zip(high.dispatched_kinds + high.active_kinds, high.statuses)) == [
        (InterventionKind.ACTIVATE_COOLING, "executed"),
        (InterventionKind.SHIFT_ACTIVITY, "executed"),
        (InterventionKind.ADVISE, "executed"),
    ]


def test_every_action_of_every_cycle_is_in_the_audit_file(tmp_path):
    timeline, audit = run_archived_day(tmp_path)
    records = audit.read_all()
    total = sum(len(step.statuses) for step in timeline.steps)
    assert total == 57
    assert len(records) == total
    for step in timeline.steps:
        pairs = list(zip(step.dispatched_kinds + step.active_kinds, step.statuses))
        logged = sorted((r.intervention.kind, r.status) for r in records if r.at == step.at)
        assert sorted(pairs) == logged


def test_a_refused_escalation_becomes_a_pending_request_that_an_approval_executes(tmp_path):
    path = write_extreme_fixture(tmp_path / "extreme.json")
    audit = AuditLog(tmp_path / "audit.jsonl")
    queue = ApprovalQueue(audit)
    timeline = run_day("synthetic-extreme", PopulationGroup.OUTDOOR_WORKER, path,
                       ApprovalGate(), audit, queue)

    assert [step.level for step in timeline.steps] == [RiskLevel.MODERATE, RiskLevel.EXTREME, RiskLevel.HIGH]
    extreme = timeline.steps[1]
    assert extreme.dispatched_kinds == [InterventionKind.ESCALATE, InterventionKind.ACTIVATE_COOLING]
    assert extreme.active_kinds == [InterventionKind.SHIFT_ACTIVITY, InterventionKind.ADVISE]
    assert extreme.statuses == ["refused", "executed", "executed", "executed"]
    assert list(zip(extreme.dispatched_kinds + extreme.active_kinds, extreme.statuses)) == [
        (InterventionKind.ESCALATE, "refused"),
        (InterventionKind.ACTIVATE_COOLING, "executed"),
        (InterventionKind.SHIFT_ACTIVITY, "executed"),
        (InterventionKind.ADVISE, "executed"),
    ]
    logged = [r.intervention.kind for r in audit.read_all() if r.at == extreme.at]
    assert logged == [InterventionKind.ESCALATE, InterventionKind.SHIFT_ACTIVITY,
                      InterventionKind.ACTIVATE_COOLING, InterventionKind.ADVISE]

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
    assert len(written) == 10
    assert written[-1].status == "executed"
    assert written[-1].approved_by == APPROVER
    assert queue.pending() == []


def test_an_unusable_fixture_fails_loudly_and_names_the_file(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({
        "meta": {"zone_id": "synthetic-empty", "latitude": 25.202108,
                 "longitude": 55.302376, "dataset": "synthetic test vector"},
        "hours": [],
    }), encoding="utf-8")
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(ValueError, match="no hours"):
        run_day("synthetic-empty", PopulationGroup.SCHOOL, empty, ApprovalGate(), audit)
    with pytest.raises(KeyError) as unknown_zone:
        run_day("dubai", PopulationGroup.SCHOOL, empty, ApprovalGate(), audit)
    assert str(empty) in unknown_zone.value.args[0]
    assert "dubai" in unknown_zone.value.args[0]


def test_a_malformed_fixture_names_the_file_in_the_error(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"hours": []}), encoding="utf-8")
    audit = AuditLog(tmp_path / "audit.jsonl")
    with pytest.raises(KeyError) as malformed:
        run_day("synthetic-broken", PopulationGroup.SCHOOL, broken, ApprovalGate(), audit)
    assert str(broken) in malformed.value.args[0]
    assert "meta" in malformed.value.args[0]


def test_the_day_runs_offline(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("the supervisor must not touch the network")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    timeline, _ = run_archived_day(tmp_path)
    assert len(timeline.steps) == 24
    assert timeline.peak_at == datetime.fromisoformat("2026-07-01T11:00:00+04:00")


def test_a_persisted_hazard_keeps_one_open_request_refreshed_to_the_peak(tmp_path):
    fixture = Path(__file__).resolve().parents[1] / "data" / "dubai_hourly_2026-08-13.json"
    audit = AuditLog(tmp_path / "audit.jsonl")
    queue = ApprovalQueue(audit)
    timeline = run_day("dubai-2026-08-13", PopulationGroup.SCHOOL, fixture,
                       ApprovalGate(), audit, queue)

    refusals = [record for record in audit.read_all() if record.status == "refused"]
    assert len(refusals) == 8
    assert len(timeline.pending_ids) == 1
    pending = queue.get(timeline.pending_ids[0])
    assert pending.intervention.kind is InterventionKind.ESCALATE
    assert pending.severity == pytest.approx(34.5)
    assert pending.refreshed_at is not None
    assert pending.requested_at <= pending.refreshed_at
    assert timeline.peak_wbgt_c == pytest.approx(34.5)
    assert timeline.peak_at == datetime.fromisoformat("2026-08-13T14:00:00+04:00")

    record = queue.decide(pending.request_id, APPROVER, approve=True)
    assert record.status == "executed"
    assert len(audit.read_all()) == 69
