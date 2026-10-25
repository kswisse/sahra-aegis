from typing import Any

from ..coordinator import AgentBase
from ..protocol import AgentRole, AssessmentPayload, Message, MessageKind
from ..risk import assess
from ..types import HeatState, PopulationGroup, RiskAssessment


class PredictAgent(AgentBase):
    """Turns an observation into a risk assessment for one group."""

    role = AgentRole.PREDICT
    emits = frozenset({MessageKind.ASSESSMENT})

    def __init__(self, group: PopulationGroup, context: dict[str, Any]) -> None:
        self.group = group
        self.context = context
        self.last_state: HeatState | None = None
        self.last_assessment: RiskAssessment | None = None

    def handle(self, message: Message) -> list[Message]:
        state = message.payload.state
        assessment = assess(state, self.group)
        self.last_state, self.last_assessment = state, assessment
        # Shared per-cycle context: Act needs the sensed state for its trace.
        self.context["state"], self.context["assessment"] = state, assessment
        return [
            self.emit(
                MessageKind.ASSESSMENT,
                AgentRole.PLAN,
                AssessmentPayload(assessment=assessment),
                message.correlation_id,
            )
        ]
