from datetime import datetime, timezone

from sahra.agents.verify import verify
from sahra.audit import AuditLog
from sahra.gate import ApprovalGate
from sahra.kernel import run_cycle
from sahra.protocol import (
    AgentRole,
    DecisionPayload,
    DisputePayload,
    Message,
    MessageKind,
    ProposalPayload,
    RulingPayload,
    SourceReading,
)
from sahra.types import (
    ActionRecord,
    HeatState,
    Intervention,
    InterventionKind,
    PopulationGroup,
    RiskAssessment,
    RiskLevel,
    SiteReading,
    WeatherReading,
)

AT = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
CORRELATION = "cycle-1"
STATE = HeatState(zone_id="z1", at=AT, air_temp_c=40.0, humidity_pct=30.0,
                  wbgt_c=31.0, source_tier="site")
ASSESSMENT = RiskAssessment(zone_id="z1", at=AT, group=PopulationGroup.SCHOOL,
                            wbgt_c=31.0, score=0.78, level=RiskLevel.HIGH)
ADVISE = Intervention(kind=InterventionKind.ADVISE, reason="advisory",
                      expected_risk_reduction=0.1)


def _action(action_id="a1", status="executed", trace=None):
    return ActionRecord(
        action_id=action_id, intervention=ADVISE, status=status, at=AT,
        reason_trace=trace if trace is not None else ["zone=z1"],
    )


def _message(kind, sender, recipient, payload):
    return Message(correlation_id=CORRELATION, sender=sender, recipient=recipient,
                   kind=kind, payload=payload)


def _decision(*actions):
    return _message(MessageKind.DECISION, AgentRole.ACT, AgentRole.VERIFY,
                    DecisionPayload(actions=list(actions)))


def _proposal(*interventions):
    return _message(MessageKind.PROPOSAL, AgentRole.PLAN, AgentRole.ACT,
                    ProposalPayload(state=STATE, assessment=ASSESSMENT,
                                    interventions=list(interventions)))


def _dispute(site_c=29.0, weather_c=31.1):
    return _message(
        MessageKind.DISPUTE, AgentRole.PREDICT, AgentRole.ARBITER,
        DisputePayload(topic="wbgt-tier-conflict", threshold_c=1.0, readings=[
            SourceReading(source="site", value_c=site_c),
            SourceReading(source="weather-outdoor", value_c=weather_c),
        ]))


def _ruling(chosen_c):
    return _message(
        MessageKind.RULING, AgentRole.ARBITER, AgentRole.PREDICT,
        RulingPayload(topic="wbgt-tier-conflict", policy="conservative-max",
                      chosen_c=chosen_c, reasoning="ruled"))


def test_a_refusal_without_a_gate_reason_is_flagged():
    result = verify([_decision(_action(status="refused"))])
    assert not result.ok
    assert any("has no gate_reason" in finding for finding in result.findings)


def test_a_dispute_without_exactly_one_ruling_is_flagged():
    result = verify([_dispute()])
    assert not result.ok
    assert any("has 0 rulings" in finding for finding in result.findings)

    two = verify([_dispute(), _ruling(31.1), _ruling(31.1)])
    assert any("has 2 rulings" in finding for finding in two.findings)


def test_a_ruling_below_the_disputed_maximum_is_flagged():
    result = verify([_dispute(site_c=29.0, weather_c=31.1), _ruling(29.0)])
    assert not result.ok
    assert any("below the disputed maximum 31.1" in finding
               for finding in result.findings)


def test_a_proposal_without_a_decision_is_flagged():
    result = verify([_proposal(ADVISE), _decision()])
    assert not result.ok
    assert any("proposal advise has no decision" in finding
               for finding in result.findings)


def test_a_duplicate_action_id_is_flagged():
    result = verify([_decision(_action("dup"), _action("dup"))])
    assert not result.ok
    assert any("appears more than once" in finding for finding in result.findings)


def test_a_clean_cycle_verifies_ok(tmp_path):
    result = run_cycle(
        zone_id="school-dxb-003", group=PopulationGroup.SCHOOL, at=AT,
        satellite=None,
        weather=WeatherReading(air_temp_c=39.0, humidity_pct=35.0,
                               wbgt_c=31.1),
        site=SiteReading(wbgt_c=29.0), gate=ApprovalGate(),
        audit=AuditLog(tmp_path / "audit.jsonl"),
    )
    assert result.verification is not None
    assert result.verification.ok, result.verification.findings
