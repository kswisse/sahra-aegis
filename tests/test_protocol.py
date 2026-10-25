from datetime import datetime, timezone

import pytest

from sahra.protocol import (
    AgentRole,
    Message,
    MessageKind,
    ProposalPayload,
    ProtocolViolation,
)
from sahra.types import (
    HeatState,
    Intervention,
    InterventionKind,
    PopulationGroup,
    RiskAssessment,
    RiskLevel,
)

AT = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
STATE = HeatState(zone_id="z1", at=AT, air_temp_c=40.0, humidity_pct=30.0,
                  wbgt_c=31.0, source_tier="site")
ASSESSMENT = RiskAssessment(zone_id="z1", at=AT, group=PopulationGroup.SCHOOL,
                            wbgt_c=31.0, score=0.7, level=RiskLevel.HIGH)


def test_wrong_payload_for_kind_is_rejected() -> None:
    with pytest.raises(ProtocolViolation) as excinfo:
        Message(
            correlation_id="c1",
            sender=AgentRole.ARBITER,
            recipient=AgentRole.PREDICT,
            kind=MessageKind.RULING,
            payload=ProposalPayload(
                state=STATE,
                assessment=ASSESSMENT,
                interventions=[
                    Intervention(
                        kind=InterventionKind.ADVISE,
                        reason="shade",
                        expected_risk_reduction=0.2,
                    )
                ],
            ),
            at=AT,
        )

    text = str(excinfo.value)
    assert "ruling" in text
    assert "ProposalPayload" in text
