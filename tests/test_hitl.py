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
    pending.status = "approved"                       # a caller holds a copy
    assert queue.get(pending.request_id).status == "pending"
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
    assert f"requested_at={pending.requested_at.isoformat()}" in written["reason_trace"]
    assert "source_action_id=act-refused-1" in written["reason_trace"]
    assert "declined_by=" not in " ".join(written["reason_trace"])
    decided = queue.get(pending.request_id)
    assert decided.status == "approved"
    assert decided.decided_by == APPROVER
    assert decided.decided_at is not None
    assert queue.pending() == []


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
    decided = queue.get(pending.request_id)
    assert decided.status == "declined"
    assert decided.decided_by == APPROVER
    assert decided.decided_at is not None
    assert queue.pending() == []


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
    assert "source_action_id=act-refused-1" in decision["reason_trace"]


def test_decide_rejects_a_second_decision_and_a_blank_approver(tmp_path):
    queue, path = queue_with_logged_refusal(tmp_path)
    pending = queue.request(refused_action(), ZONE)
    queue.decide(pending.request_id, APPROVER, approve=True)
    handed_out = queue.get(pending.request_id)
    handed_out.status = "pending"                    # a caller cannot reopen it
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



def refused(action_id: str, kind=InterventionKind.ESCALATE, wbgt: str = "33.5"):
    return ActionRecord(
        action_id=action_id,
        intervention=Intervention(kind=kind, reason=f"wbgt {wbgt} >= 32 extreme",
                                  expected_risk_reduction=0.4, consequential=True),
        status="refused", at=AT, approved_by=None,
        reason_trace=["tier=weather-outdoor", f"wbgt={wbgt}", "level=extreme"],
    )


def test_two_refusals_of_the_same_kind_share_one_open_request():
    queue = ApprovalQueue(AuditLog("unused.jsonl"))
    first = queue.request(refused("act-1", wbgt="33.5"), ZONE, severity=33.5)
    second = queue.request(refused("act-2", wbgt="34.5"), ZONE, severity=34.5)

    assert second.request_id == first.request_id
    assert second.severity == 34.5
    assert second.requested_at == first.requested_at
    assert second.refreshed_at is not None
    assert second.reason_trace == ["tier=weather-outdoor", "wbgt=34.5", "level=extreme"]
    assert [p.request_id for p in queue.pending()] == [first.request_id]
    assert queue._origins[first.request_id].action_id == "act-2"


def test_a_lower_reading_does_not_refresh_an_open_request():
    queue = ApprovalQueue(AuditLog("unused.jsonl"))
    first = queue.request(refused("act-1", wbgt="34.5"), ZONE, severity=34.5)
    second = queue.request(refused("act-2", wbgt="33.5"), ZONE, severity=33.5)

    assert second.request_id == first.request_id
    assert second.severity == 34.5
    assert second.refreshed_at is None
    assert queue._origins[first.request_id].action_id == "act-1"


def test_a_different_kind_opens_its_own_request():
    queue = ApprovalQueue(AuditLog("unused.jsonl"))
    escalate = queue.request(refused("act-1"), ZONE, severity=33.5)
    cooling = queue.request(refused("act-2", kind=InterventionKind.ACTIVATE_COOLING),
                            ZONE, severity=33.5)

    assert cooling.request_id != escalate.request_id
    assert len(queue.pending()) == 2


def test_after_a_decision_the_same_kind_opens_a_new_request(tmp_path):
    queue = ApprovalQueue(AuditLog(tmp_path / "audit.jsonl"))
    first = queue.request(refused("act-1"), ZONE, severity=33.5)
    queue.decide(first.request_id, APPROVER, approve=True)

    later = queue.request(refused("act-2", wbgt="34.5"), ZONE, severity=34.5)
    assert later.request_id != first.request_id
    assert queue.get(first.request_id).status == "approved"
    assert [p.request_id for p in queue.pending()] == [later.request_id]
