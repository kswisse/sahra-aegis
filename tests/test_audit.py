import json
from datetime import datetime, timezone

from sahra.audit import AuditLog
from sahra.types import ActionRecord, Intervention, InterventionKind

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def rec(action_id, approved_by=None):
    return ActionRecord(
        action_id=action_id,
        intervention=Intervention(kind=InterventionKind.ADVISE, reason="wbgt 29.4 > 28",
                                  expected_risk_reduction=0.1),
        status="executed", at=AT, approved_by=approved_by,
        reason_trace=["wbgt=29.4", "threshold=28"],
    )


def test_appends_are_readable_in_order(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append(rec("a1"))
    log.append(rec("a2"))
    assert [r.action_id for r in log.read_all()] == ["a1", "a2"]


def test_every_record_has_a_reason_trace(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.append(rec("a1"))
    assert log.read_all()[0].reason_trace


def test_log_lines_carry_no_pii_keys(tmp_path):
    p = tmp_path / "audit.jsonl"
    AuditLog(p).append(rec("a1"))
    for line in p.read_text(encoding="utf-8").splitlines():
        assert json.loads(line)
        for banned in ("student_name", "worker_name", "emirates_id", "phone", "email"):
            assert banned not in line


def test_append_does_not_rewrite_existing_lines(tmp_path):
    p = tmp_path / "audit.jsonl"
    log = AuditLog(p)
    log.append(rec("a1"))
    first = p.read_text(encoding="utf-8")
    log.append(rec("a2"))
    assert p.read_text(encoding="utf-8").startswith(first)
