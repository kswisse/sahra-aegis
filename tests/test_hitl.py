import json
from datetime import datetime, timezone

import pytest
from sahra.audit import AuditLog
from sahra.hitl import ApprovalQueue
from sahra.types import ActionRecord, Intervention, InterventionKind

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)
ZONE = "school-dxb-001"
APPROVER = "coordinator@schooldxb"


def refused_action():
    return ActionRecord(
        action_id="act-refused-1",
        intervention=Intervention(kind=InterventionKind.ESCALATE,
                                  reason="wbgt 33.5 >= 32 extreme",
                                  expected_risk_reduction=0.4,
                                  consequential=True),
        status="refused", at=AT, approved_by=None,
        reason_trace=["tier=site", "wbgt=33.5", "threshold=28", "level=extreme"],
    )


def queue_with_logged_refusal(tmp_path):
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.append(refused_action())
    return ApprovalQueue(log), path


def lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_request_opens_a_pending_entry_and_writes_nothing(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    pending = queue.request(refused_action(), ZONE)
    assert pending.status == "pending"
    assert pending.zone_id == ZONE
    assert pending.intervention.kind is InterventionKind.ESCALATE
    assert pending.decided_by is None
    assert pending.decided_at is None
    assert [p.request_id for p in queue.pending()] == [pending.request_id]
    assert len(lines(path)) == 1


def test_approval_appends_an_executed_record_with_the_approver(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    pending = queue.request(refused_action(), ZONE)
    record = queue.decide(pending.request_id, APPROVER, approve=True)
    assert record.status == "executed"
    assert record.approved_by == APPROVER
    assert record.intervention.kind is InterventionKind.ESCALATE
    written = json.loads(lines(path)[-1])
    assert written["status"] == "executed"
    assert written["approved_by"] == APPROVER
    assert "decision=approved" in written["reason_trace"]
    assert "declined_by=" not in " ".join(written["reason_trace"])


def test_decline_appends_a_refused_record_with_the_decliner_in_the_trace(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    pending = queue.request(refused_action(), ZONE)
    record = queue.decide(pending.request_id, APPROVER, approve=False)
    assert record.status == "refused"
    assert record.approved_by is None
    written = json.loads(lines(path)[-1])
    assert written["status"] == "refused"
    assert written["approved_by"] is None
    assert f"declined_by={APPROVER}" in written["reason_trace"]
    assert "decision=declined" in written["reason_trace"]


def test_audit_holds_the_refusal_plus_the_decision(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    pending = queue.request(refused_action(), ZONE)
    queue.decide(pending.request_id, APPROVER, approve=True)
    written = [json.loads(line) for line in lines(path)]
    assert len(written) == 2
    original, decision = written
    assert original["action_id"] == "act-refused-1"
    assert original["status"] == "refused"
    assert original["approved_by"] is None
    assert decision["status"] == "executed"
    assert decision["approved_by"] == APPROVER
    assert decision["action_id"] != original["action_id"]


def test_decide_rejects_a_second_decision_and_a_blank_approver(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    pending = queue.request(refused_action(), ZONE)
    queue.decide(pending.request_id, APPROVER, approve=True)
    with pytest.raises(ValueError):
        queue.decide(pending.request_id, APPROVER, approve=True)
    blank = queue.request(refused_action(), ZONE)
    with pytest.raises(ValueError):
        queue.decide(blank.request_id, "   ", approve=True)
    assert len(lines(path)) == 2
    assert [p.request_id for p in queue.pending()] == [blank.request_id]


def test_unknown_request_id_raises_key_error(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    with pytest.raises(KeyError):
        queue.get("does-not-exist")
    with pytest.raises(KeyError):
        queue.decide("does-not-exist", APPROVER, approve=True)
    assert len(lines(path)) == 1
