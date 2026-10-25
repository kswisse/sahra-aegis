from datetime import datetime, timezone

from sahra.audit import AuditLog
from sahra.gate import ApprovalGate
from sahra.kernel import run_cycle
from sahra.protocol import MessageKind
from sahra.types import PopulationGroup, SiteReading, WeatherReading

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


def test_one_cycle_emits_the_four_messages_in_order(tmp_path):
    r = run(tmp_path, 31.0)
    kinds = [message.kind for message in r.transcript]
    assert kinds == [
        MessageKind.OBSERVATION,
        MessageKind.ASSESSMENT,
        MessageKind.PROPOSAL,
        MessageKind.DECISION,
    ]
    assert len({message.correlation_id for message in r.transcript}) == 1


def test_decision_message_carries_the_cycle_actions(tmp_path):
    r = run(tmp_path, 31.0)
    decision = next(m for m in r.transcript if m.kind is MessageKind.DECISION)
    assert [a.action_id for a in decision.payload.actions] == [
        a.action_id for a in r.actions]


def test_two_identical_cycles_emit_the_same_sequence(tmp_path):
    first = run(tmp_path, 31.0)
    second = run(tmp_path, 31.0)

    def shape(result):
        return [(m.sender, m.recipient, m.kind) for m in result.transcript]

    assert shape(first) == shape(second)


def test_refused_escalation_keeps_its_gate_reason_and_zone(tmp_path):
    r = run(tmp_path, 33.5)
    decision = next(m for m in r.transcript if m.kind is MessageKind.DECISION)
    refused = [a for a in decision.payload.actions if a.status == "refused"]
    assert len(refused) == 1
    trace = refused[0].reason_trace
    assert "zone=school-dxb-001" in trace
    gate_reason = next(item for item in trace if item.startswith("gate_reason="))
    assert "human approval required" in gate_reason
