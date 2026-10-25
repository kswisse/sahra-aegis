from ..coordinator import AgentBase
from ..protocol import (
    AgentRole,
    Message,
    MessageKind,
    ProtocolViolation,
    RulingPayload,
)


class ArbiterAgent(AgentBase):
    """Rules when two sources report different indices.

    The policy is conservative-max: the higher index wins, because an unresolved
    conflict in a heat-safety decision must fail towards protecting people. The
    ruling names both readings and the one it took, so the decision it produced
    can be audited later.
    """

    role = AgentRole.ARBITER
    emits = frozenset({MessageKind.RULING})
    policy = "conservative-max"

    def __init__(self) -> None:
        self.last_ruling: RulingPayload | None = None

    def handle(self, message: Message) -> list[Message]:
        if message.kind is not MessageKind.DISPUTE:
            raise ProtocolViolation(
                f"arbiter expects a dispute, got {message.kind.value}")
        readings = message.payload.readings
        higher = max(readings, key=lambda reading: reading.value_c)
        gap = abs(readings[0].value_c - readings[1].value_c)
        reasoning = (
            f"tiers disagree: {readings[0].source} {readings[0].value_c:.1f} C vs "
            f"{readings[1].source} {readings[1].value_c:.1f} C, gap {gap:.1f} C; "
            f"chose the higher, conservative {higher.value_c:.1f} C from {higher.source}")
        self.last_ruling = RulingPayload(
            topic=message.payload.topic,
            policy=self.policy,
            chosen_c=higher.value_c,
            reasoning=reasoning,
        )
        return [
            self.emit(
                MessageKind.RULING,
                AgentRole.PREDICT,
                self.last_ruling,
                message.correlation_id,
            )
        ]
