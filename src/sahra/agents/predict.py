from ..coordinator import AgentBase
from ..fusion import TIER_DISAGREEMENT_C
from ..protocol import (
    AgentRole,
    AssessmentPayload,
    DisputePayload,
    Message,
    MessageKind,
    RulingPayload,
    SourceReading,
)
from ..risk import assess
from ..types import HeatState, PopulationGroup, RiskAssessment


class PredictAgent(AgentBase):
    """Turns an observation into a risk assessment for one group.

    When the site sensor and the weather tier disagree by more than
    TIER_DISAGREEMENT_C, this agent does not pick a value: it raises a dispute
    and waits for the arbiter's ruling before it assesses anything.
    """

    role = AgentRole.PREDICT
    emits = frozenset({MessageKind.ASSESSMENT, MessageKind.DISPUTE})

    def __init__(self, group: PopulationGroup) -> None:
        self.group = group
        self.last_state: HeatState | None = None
        self.last_assessment: RiskAssessment | None = None
        self._pending: dict[str, tuple[HeatState, str, float, float]] = {}

    def handle(self, message: Message) -> list[Message]:
        if message.kind is MessageKind.RULING:
            return self._rule(message)

        payload = message.payload
        state = payload.state
        site_c, weather_c = payload.site_wbgt_c, payload.weather_wbgt_c
        if (
            site_c is not None
            and weather_c is not None
            and abs(site_c - weather_c) > TIER_DISAGREEMENT_C
        ):
            self._pending[message.correlation_id] = (
                state, payload.weather_tier, site_c, weather_c)
            return [
                self.emit(
                    MessageKind.DISPUTE,
                    AgentRole.ARBITER,
                    DisputePayload(
                        topic="wbgt-tier-conflict",
                        readings=[
                            SourceReading(source="site", value_c=site_c),
                            SourceReading(
                                source=payload.weather_tier, value_c=weather_c),
                        ],
                        threshold_c=TIER_DISAGREEMENT_C,
                    ),
                    message.correlation_id,
                )
            ]
        return [self._assess(state, message.correlation_id)]

    def _rule(self, message: Message) -> list[Message]:
        state, weather_tier, site_c, weather_c = self._pending.pop(
            message.correlation_id)
        ruling: RulingPayload = message.payload
        tier = "site" if site_c >= weather_c else weather_tier
        notes = [ruling.reasoning]
        if state.disagreement:
            notes.append(state.disagreement)
        resolved = state.model_copy(update={
            "wbgt_c": ruling.chosen_c,
            "source_tier": tier,
            "disagreement": "; ".join(notes),
        })
        return [self._assess(resolved, message.correlation_id)]

    def _assess(self, state: HeatState, correlation_id: str) -> Message:
        assessment = assess(state, self.group)
        self.last_state, self.last_assessment = state, assessment
        return self.emit(
            MessageKind.ASSESSMENT,
            AgentRole.PLAN,
            AssessmentPayload(state=state, assessment=assessment),
            correlation_id,
        )
