from datetime import datetime, timezone

import pytest

from sahra.coordinator import AgentBase, AgentCoordinator
from sahra.protocol import (
    AgentRole,
    AssessmentPayload,
    DecisionPayload,
    Message,
    MessageKind,
    ObservationPayload,
    ProposalPayload,
    ProtocolViolation,
    RulingPayload,
)
from sahra.types import (
    HeatState,
    Intervention,
    InterventionKind,
    PopulationGroup,
    RiskAssessment,
    RiskLevel,
)

CORRELATION = "cycle-1"
NOW = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)


def _state() -> HeatState:
    return HeatState(
        zone_id="z1",
        at=NOW,
        air_temp_c=40.0,
        humidity_pct=30.0,
        wbgt_c=31.0,
        source_tier="site",
    )


def _assessment() -> RiskAssessment:
    return RiskAssessment(
        zone_id="z1",
        at=NOW,
        group=PopulationGroup.SCHOOL,
        wbgt_c=31.0,
        score=0.7,
        level=RiskLevel.HIGH,
    )


def _intervention() -> Intervention:
    return Intervention(
        kind=InterventionKind.SHIFT_ACTIVITY,
        reason="move to shade",
        expected_risk_reduction=0.3,
    )


def _seed() -> Message:
    return Message(
        correlation_id=CORRELATION,
        sender=AgentRole.MONITOR,
        recipient=AgentRole.PREDICT,
        kind=MessageKind.OBSERVATION,
        payload=ObservationPayload(state=_state()),
    )


class Monitor(AgentBase):
    role = AgentRole.MONITOR
    emits = frozenset({MessageKind.OBSERVATION})

    def handle(self, message: Message) -> list[Message]:
        return []


class Predict(AgentBase):
    role = AgentRole.PREDICT
    emits = frozenset({MessageKind.ASSESSMENT})

    def handle(self, message: Message) -> list[Message]:
        return [
            self.emit(
                MessageKind.ASSESSMENT,
                AgentRole.PLAN,
                AssessmentPayload(assessment=_assessment()),
                message.correlation_id,
            )
        ]


class Plan(AgentBase):
    role = AgentRole.PLAN
    emits = frozenset({MessageKind.PROPOSAL})

    def handle(self, message: Message) -> list[Message]:
        return [
            self.emit(
                MessageKind.PROPOSAL,
                AgentRole.ACT,
                ProposalPayload(interventions=[_intervention()]),
                message.correlation_id,
            )
        ]


class Act(AgentBase):
    role = AgentRole.ACT
    emits = frozenset({MessageKind.DECISION})

    def handle(self, message: Message) -> list[Message]:
        return []


def _chain_agents() -> dict[AgentRole, AgentBase]:
    return {
        AgentRole.MONITOR: Monitor(),
        AgentRole.PREDICT: Predict(),
        AgentRole.PLAN: Plan(),
        AgentRole.ACT: Act(),
    }


def test_three_hop_chain_transcript_in_order() -> None:
    transcript = AgentCoordinator(_chain_agents()).run([_seed()])

    assert [
        (message.sender, message.recipient, message.kind) for message in transcript
    ] == [
        (AgentRole.MONITOR, AgentRole.PREDICT, MessageKind.OBSERVATION),
        (AgentRole.PREDICT, AgentRole.PLAN, MessageKind.ASSESSMENT),
        (AgentRole.PLAN, AgentRole.ACT, MessageKind.PROPOSAL),
    ]


class OverreachingAct(AgentBase):
    role = AgentRole.ACT
    emits = frozenset({MessageKind.DECISION})

    def handle(self, message: Message) -> list[Message]:
        return [
            Message(
                correlation_id=message.correlation_id,
                sender=AgentRole.ACT,
                recipient=AgentRole.PREDICT,
                kind=MessageKind.RULING,
                payload=RulingPayload(
                    topic="tier gap",
                    policy="conservative-max",
                    chosen_c=31.0,
                    reasoning="higher wins",
                ),
            )
        ]


def test_undeclared_kind_raises_and_transcript_stays_valid() -> None:
    agents = {
        AgentRole.PLAN: Plan(),
        AgentRole.ACT: OverreachingAct(),
        AgentRole.PREDICT: Predict(),
    }
    seed = Message(
        correlation_id=CORRELATION,
        sender=AgentRole.PLAN,
        recipient=AgentRole.ACT,
        kind=MessageKind.PROPOSAL,
        payload=ProposalPayload(interventions=[_intervention()]),
    )
    coordinator = AgentCoordinator(agents)

    with pytest.raises(ProtocolViolation):
        coordinator.run([seed])

    # The seed was delivered before Act's reply was validated; the rejected
    # ruling is never appended, so the transcript holds only the seed.
    assert coordinator.transcript == (seed,)


def test_emit_sender_is_agent_role_and_forged_sender_rejected() -> None:
    act = Act()
    emitted = act.emit(
        MessageKind.DECISION,
        AgentRole.VERIFY,
        DecisionPayload(actions=[]),
        CORRELATION,
    )
    assert emitted.sender is AgentRole.ACT

    unregistered = Message(
        correlation_id=CORRELATION,
        sender=AgentRole.ARBITER,
        recipient=AgentRole.PREDICT,
        kind=MessageKind.RULING,
        payload=RulingPayload(
            topic="tier gap",
            policy="conservative-max",
            chosen_c=31.0,
            reasoning="higher wins",
        ),
    )
    with pytest.raises(ProtocolViolation):
        AgentCoordinator(_chain_agents()).run([unregistered])

    mismatched = Message(
        correlation_id=CORRELATION,
        sender=AgentRole.ACT,
        recipient=AgentRole.PREDICT,
        kind=MessageKind.RULING,
        payload=RulingPayload(
            topic="tier gap",
            policy="conservative-max",
            chosen_c=31.0,
            reasoning="higher wins",
        ),
    )
    with pytest.raises(ProtocolViolation):
        AgentCoordinator(_chain_agents()).run([mismatched])


def test_two_runs_identical_transcript() -> None:
    first = AgentCoordinator(_chain_agents()).run([_seed()])
    second = AgentCoordinator(_chain_agents()).run([_seed()])

    shape = lambda transcript: [
        (message.sender, message.recipient, message.kind, message.payload)
        for message in transcript
    ]
    assert shape(first) == shape(second)
