from ..coordinator import AgentBase
from ..planner import plan
from ..protocol import AgentRole, Message, MessageKind, ProposalPayload
from ..types import Intervention


class PlanAgent(AgentBase):
    """Proposes the interventions an assessment calls for."""

    role = AgentRole.PLAN
    emits = frozenset({MessageKind.PROPOSAL})

    def __init__(self) -> None:
        self.last_interventions: list[Intervention] = []

    def handle(self, message: Message) -> list[Message]:
        interventions = plan(message.payload.assessment)
        self.last_interventions = interventions
        return [
            self.emit(
                MessageKind.PROPOSAL,
                AgentRole.ACT,
                ProposalPayload(
                    state=message.payload.state,
                    assessment=message.payload.assessment,
                    interventions=interventions,
                ),
                message.correlation_id,
            )
        ]
