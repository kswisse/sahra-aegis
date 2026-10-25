from datetime import datetime, timezone

import pytest

from sahra.protocol import (
    AgentRole,
    Message,
    MessageKind,
    ProposalPayload,
    ProtocolViolation,
)
from sahra.types import Intervention, InterventionKind


def test_wrong_payload_for_kind_is_rejected() -> None:
    with pytest.raises(ProtocolViolation) as excinfo:
        Message(
            correlation_id="c1",
            sender=AgentRole.ARBITER,
            recipient=AgentRole.PREDICT,
            kind=MessageKind.RULING,
            payload=ProposalPayload(
                interventions=[
                    Intervention(
                        kind=InterventionKind.ADVISE,
                        reason="shade",
                        expected_risk_reduction=0.2,
                    )
                ]
            ),
            at=datetime(2026, 7, 1, 12, tzinfo=timezone.utc),
        )

    text = str(excinfo.value)
    assert "ruling" in text
    assert "ProposalPayload" in text
