from .types import Intervention


class ApprovalRequired(Exception):
    """Raised when a consequential intervention has no human approver."""


class ApprovalGate:
    """Schema-enforced structural guardrail: consequential actions are refused,
    never silently downgraded."""

    def authorize(self, intervention: Intervention, approved_by: str | None) -> Intervention:
        if intervention.consequential and not approved_by:
            raise ApprovalRequired(
                f"human approval required for consequential intervention: {intervention.kind.value}"
            )
        return intervention
