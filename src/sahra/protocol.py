from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .types import ActionRecord, HeatState, Intervention, RiskAssessment


class AgentRole(str, Enum):
    MONITOR = "monitor"
    PREDICT = "predict"
    PLAN = "plan"
    ACT = "act"
    VERIFY = "verify"
    ARBITER = "arbiter"


class MessageKind(str, Enum):
    OBSERVATION = "observation"
    ASSESSMENT = "assessment"
    DISPUTE = "dispute"
    RULING = "ruling"
    PROPOSAL = "proposal"
    DECISION = "decision"
    VERIFICATION = "verification"


class ProtocolViolation(RuntimeError):
    pass


class SourceReading(BaseModel):
    source: str
    value_c: float


class ObservationPayload(BaseModel):
    state: HeatState


class AssessmentPayload(BaseModel):
    state: HeatState
    assessment: RiskAssessment


class DisputePayload(BaseModel):
    topic: str
    readings: list[SourceReading]
    threshold_c: float


class RulingPayload(BaseModel):
    topic: str
    policy: Literal["conservative-max"]
    chosen_c: float
    reasoning: str


class ProposalPayload(BaseModel):
    state: HeatState
    assessment: RiskAssessment
    interventions: list[Intervention]


class DecisionPayload(BaseModel):
    actions: list[ActionRecord]


class VerificationPayload(BaseModel):
    ok: bool
    findings: list[str]


_PAYLOAD_BY_KIND: dict[MessageKind, type[BaseModel]] = {
    MessageKind.OBSERVATION: ObservationPayload,
    MessageKind.ASSESSMENT: AssessmentPayload,
    MessageKind.DISPUTE: DisputePayload,
    MessageKind.RULING: RulingPayload,
    MessageKind.PROPOSAL: ProposalPayload,
    MessageKind.DECISION: DecisionPayload,
    MessageKind.VERIFICATION: VerificationPayload,
}


class Message(BaseModel):
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    correlation_id: str
    sender: AgentRole
    recipient: AgentRole
    kind: MessageKind
    payload: Any
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _payload_matches_kind(self) -> "Message":
        expected = _PAYLOAD_BY_KIND[self.kind]
        if not isinstance(self.payload, expected):
            raise ProtocolViolation(
                f"kind {self.kind.value} expects {expected.__name__}, "
                f"got {type(self.payload).__name__}")
        return self
