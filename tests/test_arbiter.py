from datetime import datetime, timezone

import pytest

from sahra.agents import ArbiterAgent, PredictAgent
from sahra.audit import AuditLog
from sahra.coordinator import AgentCoordinator
from sahra.gate import ApprovalGate
from sahra.kernel import run_cycle
from sahra.protocol import (
    AgentRole,
    AssessmentPayload,
    Message,
    MessageKind,
    ProtocolViolation,
    RulingPayload,
)
from sahra.types import (
    HeatState,
    PopulationGroup,
    RiskAssessment,
    RiskLevel,
    SatelliteReading,
    SiteReading,
    WeatherReading,
)

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)
WX = WeatherReading(air_temp_c=39.0, humidity_pct=35.0, wbgt_c=31.1, solar_wm2=500.0)
STATE = HeatState(zone_id="z1", at=AT, air_temp_c=40.0, humidity_pct=30.0,
                  wbgt_c=31.0, source_tier="site")
ASSESSMENT = RiskAssessment(zone_id="z1", at=AT, group=PopulationGroup.SCHOOL,
                            wbgt_c=31.0, score=0.7, level=RiskLevel.HIGH)


def run(tmp_path, site_wbgt=29.0, weather=WX, satellite=None):
    return run_cycle(
        zone_id="school-dxb-003", group=PopulationGroup.SCHOOL, at=AT,
        satellite=satellite, weather=weather,
        site=SiteReading(wbgt_c=site_wbgt) if site_wbgt is not None else None,
        gate=ApprovalGate(), audit=AuditLog(tmp_path / "audit.jsonl"),
    )


def kinds(result):
    return [message.kind for message in result.transcript]


def test_a_tier_conflict_is_disputed_then_ruled_on(tmp_path):
    r = run(tmp_path)
    assert kinds(r) == [
        MessageKind.OBSERVATION,
        MessageKind.DISPUTE,
        MessageKind.RULING,
        MessageKind.ASSESSMENT,
        MessageKind.PROPOSAL,
        MessageKind.DECISION,
    ]
    assert len({message.correlation_id for message in r.transcript}) == 1
    dispute = next(m for m in r.transcript if m.kind is MessageKind.DISPUTE)
    ruling = next(m for m in r.transcript if m.kind is MessageKind.RULING)
    assert dispute.sender is AgentRole.PREDICT
    assert dispute.recipient is AgentRole.ARBITER
    assert ruling.sender is AgentRole.ARBITER
    assert ruling.recipient is AgentRole.PREDICT
    assert ruling.correlation_id == dispute.correlation_id


def test_the_ruling_takes_the_higher_index_and_says_so(tmp_path):
    r = run(tmp_path)
    assert r.state.wbgt_c == 31.1
    assert r.state.source_tier == "weather-outdoor"
    assert r.state.disagreement == (
        "tiers disagree: site 29.0 C vs weather-outdoor 31.1 C, gap 2.1 C; "
        "chose the higher, conservative 31.1 C from weather-outdoor")
    assert any(f"disagreement={r.state.disagreement}" in item
               for item in r.actions[0].reason_trace)


def test_a_higher_site_reading_keeps_the_site_tier(tmp_path):
    wx = WeatherReading(air_temp_c=39.0, humidity_pct=35.0, wbgt_c=30.0)
    r = run(tmp_path, site_wbgt=32.5, weather=wx)
    assert r.state.wbgt_c == 32.5
    assert r.state.source_tier == "site"
    assert "chose the higher, conservative 32.5 C from site" in r.state.disagreement


def test_a_gap_within_the_threshold_is_not_disputed(tmp_path):
    wx = WeatherReading(air_temp_c=41.0, humidity_pct=62.0, wbgt_c=32.3)
    r = run(tmp_path, site_wbgt=31.5, weather=wx)
    assert MessageKind.DISPUTE not in kinds(r)
    assert r.state.wbgt_c == 31.5
    assert r.state.disagreement is None


def test_a_satellite_advisory_alone_is_not_disputed(tmp_path):
    r = run(tmp_path, site_wbgt=None, satellite=SatelliteReading(lst_c=60.0))
    assert MessageKind.DISPUTE not in kinds(r)
    assert "advisory only" in r.state.disagreement
    assert "tiers disagree" not in r.state.disagreement


def test_only_the_arbiter_may_emit_a_ruling():
    coordinator = AgentCoordinator(
        {AgentRole.PREDICT: PredictAgent(PopulationGroup.SCHOOL)})
    forged = Message(
        correlation_id="c1",
        sender=AgentRole.PREDICT,
        recipient=AgentRole.PREDICT,
        kind=MessageKind.RULING,
        payload=RulingPayload(
            topic="wbgt-tier-conflict",
            policy="conservative-max",
            chosen_c=31.1,
            reasoning="forged",
        ),
    )
    with pytest.raises(ProtocolViolation, match="may not emit ruling"):
        coordinator.run([forged])


def test_a_gap_of_exactly_one_degree_is_not_disputed(tmp_path):
    wx = WeatherReading(air_temp_c=41.0, humidity_pct=62.0, wbgt_c=32.0)
    r = run(tmp_path, site_wbgt=31.0, weather=wx)
    assert MessageKind.DISPUTE not in kinds(r)
    assert r.state.wbgt_c == 31.0


def test_a_ruling_with_no_pending_dispute_is_rejected():
    predict = PredictAgent(PopulationGroup.SCHOOL)
    orphan = Message(
        correlation_id="never-disputed",
        sender=AgentRole.ARBITER,
        recipient=AgentRole.PREDICT,
        kind=MessageKind.RULING,
        payload=RulingPayload(
            topic="wbgt-tier-conflict",
            policy="conservative-max",
            chosen_c=31.1,
            reasoning="unsolicited",
        ),
    )
    with pytest.raises(ProtocolViolation, match="no pending dispute"):
        predict.handle(orphan)


def test_the_arbiter_rejects_a_non_dispute():
    message = Message(
        correlation_id="c1",
        sender=AgentRole.PREDICT,
        recipient=AgentRole.ARBITER,
        kind=MessageKind.ASSESSMENT,
        payload=AssessmentPayload(state=STATE, assessment=ASSESSMENT),
    )
    with pytest.raises(ProtocolViolation, match="expects a dispute"):
        ArbiterAgent().handle(message)
