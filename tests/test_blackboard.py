from datetime import datetime, timedelta, timezone

from sahra.audit import AuditLog
from sahra.blackboard import Blackboard
from sahra.gate import ApprovalGate
from sahra.hitl import ApprovalQueue
from sahra.kernel import run_cycle
from sahra.types import PopulationGroup, WeatherReading

AT = datetime(2026, 8, 13, 10, 0, tzinfo=timezone.utc)
ZONE = "dubai-2026-08-13"
EXTREME = WeatherReading(air_temp_c=45.0, humidity_pct=70.0, wbgt_c=40.0)


def run(tmp_path, audit, board, hour):
    return run_cycle(
        zone_id=ZONE, group=PopulationGroup.SCHOOL, at=AT + timedelta(hours=hour),
        satellite=None, weather=EXTREME, site=None,
        gate=ApprovalGate(), audit=audit, blackboard=board,
    )


def refusals(result):
    return [action for action in result.actions
            if action.status == "refused" and action.intervention.consequential]


def test_eight_extreme_hours_link_every_refusal_to_the_open_request(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    queue = ApprovalQueue(audit)
    board = Blackboard()
    opened = []

    for hour in range(8):
        result = run(tmp_path, audit, board, hour)
        result_refusals = refusals(result)
        assert len(result_refusals) == 1
        opened.append(
            queue.request(result_refusals[0], ZONE,
                          severity=result.assessment.wbgt_c).request_id)
        board.sync(queue.pending())

    assert len(set(opened)) == 1
    assert len(queue.pending()) == 1
    records = [r for r in audit.read_all() if r.status == "refused"]
    assert len(records) == 8
    assert not any(item.startswith("linked_request=")
                   for item in records[0].reason_trace)
    for index, record in enumerate(records[1:], start=1):
        assert f"linked_request={opened[index - 1]}" in record.reason_trace
    assert board.refused_bands[(ZONE, "escalate")]


def test_a_decision_clears_the_link_and_the_next_refusal_opens_a_new_request(tmp_path):
    audit = AuditLog(tmp_path / "audit.jsonl")
    queue = ApprovalQueue(audit)
    board = Blackboard()

    first = run(tmp_path, audit, board, 0)
    first_id = queue.request(refusals(first)[0], ZONE).request_id
    board.sync(queue.pending())

    linked = run(tmp_path, audit, board, 1)
    linked_trace = refusals(linked)[0].reason_trace
    assert f"linked_request={first_id}" in linked_trace

    queue.decide(first_id, "reviewer@dxbops", approve=True)
    board.sync(queue.pending())
    assert board.link_for(ZONE, refusals(linked)[0].intervention.kind) is None

    unlinked = run(tmp_path, audit, board, 2)
    assert not any(item.startswith("linked_request=")
                   for item in refusals(unlinked)[0].reason_trace)
    second_id = queue.request(refusals(unlinked)[0], ZONE).request_id
    assert second_id != first_id
