from ..blackboard import Blackboard
from ..coordinator import AgentBase
from ..planner import plan
from ..protocol import AgentRole, Message, MessageKind, ProposalPayload
from ..types import Intervention


class PlanAgent(AgentBase):
    """Proposes the interventions an assessment calls for."""

    role = AgentRole.PLAN
    emits = frozenset({MessageKind.PROPOSAL})

    def __init__(self, blackboard: Blackboard) -> None:
        self.blackboard = blackboard
        self.last_interventions: list[Intervention] = []

    def handle(self, message: Message) -> list[Message]:
        assessment = message.payload.assessment
        self.blackboard.observe(assessment)
        interventions = plan(assessment)
        links = {}
        for intervention in interventions:
            request_id = self.blackboard.link_for(
                assessment.zone_id, intervention.kind)
            if request_id is not None:
                links[intervention.kind.value] = request_id
        self.last_interventions = interventions
        return [
            self.emit(
                MessageKind.PROPOSAL,
                AgentRole.ACT,
                ProposalPayload(
                    state=message.payload.state,
                    assessment=assessment,
                    interventions=interventions,
                    links=links,
                ),
                message.correlation_id,
            )
        ]
