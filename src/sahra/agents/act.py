from uuid import uuid4

from ..audit import AuditLog
from ..blackboard import Blackboard
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
        blackboard: Blackboard,
    ) -> None:
        self.gate = gate
        self.audit = audit
        self.approved_by = approved_by
        self.blackboard = blackboard
        self.last_actions: list[ActionRecord] = []

    def handle(self, message: Message) -> list[Message]:
        state = message.payload.state
        assessment = message.payload.assessment
        links = message.payload.links
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
                request_id = links.get(intervention.kind.value)
                if request_id is not None:
                    trace.append(f"linked_request={request_id}")
                self.blackboard.record_refusal(
                    state.zone_id, intervention.kind, assessment.level)
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
