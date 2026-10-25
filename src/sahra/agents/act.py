from uuid import uuid4

from ..audit import AuditLog
from ..coordinator import AgentBase
from ..gate import ApprovalGate, ApprovalRequired
from ..protocol import AgentRole, DecisionPayload, Message, MessageKind
from ..risk import THRESHOLD_C
from ..types import ActionRecord


class ActAgent(AgentBase):
    """Passes each proposal through the approval gate and audits the outcome."""

    role = AgentRole.ACT
    emits = frozenset({MessageKind.DECISION})

    def __init__(
        self,
        gate: ApprovalGate,
        audit: AuditLog,
        approved_by: str | None,
    ) -> None:
        self.gate = gate
        self.audit = audit
        self.approved_by = approved_by
        self.last_actions: list[ActionRecord] = []

    def handle(self, message: Message) -> list[Message]:
        state = message.payload.state
        assessment = message.payload.assessment
        actions: list[ActionRecord] = []
        for intervention in message.payload.interventions:
            trace = [
                f"tier={state.source_tier}",
                f"wbgt={assessment.wbgt_c}",
                f"threshold={THRESHOLD_C}",
                f"level={assessment.level.value}",
                f"expected_risk_reduction={intervention.expected_risk_reduction}",
                f"zone={state.zone_id}",
            ]
            if state.disagreement:
                trace.append(f"disagreement={state.disagreement}")
            try:
                self.gate.authorize(intervention, self.approved_by)
                status, approver = "executed", self.approved_by
            except ApprovalRequired as exc:
                trace.append(f"gate_reason={exc}")
                status, approver = "refused", None
            record = ActionRecord(
                action_id=uuid4().hex[:12], intervention=intervention, status=status,
                at=state.at, approved_by=approver, reason_trace=trace,
            )
            self.audit.append(record)
            actions.append(record)
        self.last_actions = actions
        return [
            self.emit(
                MessageKind.DECISION,
                AgentRole.VERIFY,
                DecisionPayload(actions=actions),
                message.correlation_id,
            )
        ]
