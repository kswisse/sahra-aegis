from collections.abc import Sequence

from ..coordinator import AgentBase
from ..protocol import AgentRole, Message, MessageKind, VerificationPayload


def verify(transcript: Sequence[Message]) -> VerificationPayload:
    """Check one cycle's messages against the invariants. Read-only.

    A finding is recorded, never acted on: the decisions this transcript
    produced are already written and are not rewritten by the verifier.
    """
    findings: list[str] = []
    proposals = [m for m in transcript if m.kind is MessageKind.PROPOSAL]
    decisions = [m for m in transcript if m.kind is MessageKind.DECISION]
    disputes = [m for m in transcript if m.kind is MessageKind.DISPUTE]
    rulings = [m for m in transcript if m.kind is MessageKind.RULING]

    decided: set[tuple[str, str]] = set()
    seen_actions: set[str] = set()
    for message in decisions:
        for action in message.payload.actions:
            decided.add((message.correlation_id, action.intervention.kind.value))
            if action.action_id in seen_actions:
                findings.append(
                    f"action_id {action.action_id} appears more than once")
            seen_actions.add(action.action_id)
            if action.status == "refused" and not any(
                    item.startswith("gate_reason=") for item in action.reason_trace):
                findings.append(
                    f"refused action {action.action_id} has no gate_reason")

    for message in proposals:
        for intervention in message.payload.interventions:
            if (message.correlation_id, intervention.kind.value) not in decided:
                findings.append(
                    f"proposal {intervention.kind.value} has no decision "
                    f"in cycle {message.correlation_id}")

    for dispute in disputes:
        matching = [r for r in rulings
                    if r.correlation_id == dispute.correlation_id]
        if len(matching) != 1:
            findings.append(
                f"dispute in cycle {dispute.correlation_id} has "
                f"{len(matching)} rulings")
            continue
        ceiling = max(reading.value_c for reading in dispute.payload.readings)
        if matching[0].payload.chosen_c < ceiling:
            findings.append(
                f"ruling in cycle {dispute.correlation_id} chose "
                f"{matching[0].payload.chosen_c} below the disputed "
                f"maximum {ceiling}")

    disputed = {dispute.correlation_id for dispute in disputes}
    for ruling in rulings:
        if ruling.correlation_id not in disputed:
            findings.append(
                f"ruling in cycle {ruling.correlation_id} has no dispute")

    return VerificationPayload(ok=not findings, findings=findings)


class VerifyAgent(AgentBase):
    """Verifies the cycle it just watched, and lets the decision stand."""

    role = AgentRole.VERIFY
    emits = frozenset()

    def __init__(self) -> None:
        self.last_result: VerificationPayload | None = None

    def handle(self, message: Message) -> list[Message]:
        self.last_result = verify(self.coordinator.transcript)
        return []
