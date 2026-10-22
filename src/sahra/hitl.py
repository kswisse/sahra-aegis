from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel

from .audit import AuditLog
from .types import ActionRecord, Intervention


class PendingApproval(BaseModel):
    """A consequential action waiting for a human decision."""

    request_id: str
    zone_id: str
    intervention: Intervention
    requested_at: datetime
    reason_trace: list[str]
    severity: float | None = None
    refreshed_at: datetime | None = None
    status: str = "pending"
    decided_by: str | None = None
    decided_at: datetime | None = None


class ApprovalQueue:
    """Human-in-the-loop approval queue.

    A refused consequential action becomes a pending request; the coordinator's
    decision is appended to the append-only audit as a new record. The original
    refusal is never rewritten.

    The queue holds at most one open request per (zone, intervention kind), so a
    hazard that persists for hours does not flood it. Every hour is still
    refused and still written to the audit; only the queue is deduped, and an
    open request is refreshed in place to the worst reading it has seen.
    """

    def __init__(self, audit: AuditLog):
        self.audit = audit
        self._requests: dict[str, PendingApproval] = {}
        self._origins: dict[str, ActionRecord] = {}

    def request(self, action: ActionRecord, zone_id: str,
                severity: float | None = None) -> PendingApproval:
        """Open a pending request for an already-refused action. Writes nothing.

        If an open request already covers this zone and kind, it is refreshed
        to the newer refusal when `severity` is higher (or was unset), and the
        same request_id is returned. A decision closes the window: the next
        refusal of that kind opens a new request.
        """
        for existing in self._requests.values():
            if (existing.status == "pending" and existing.zone_id == zone_id
                    and existing.intervention.kind == action.intervention.kind):
                if severity is not None and (existing.severity is None
                                             or severity > existing.severity):
                    existing.intervention = action.intervention
                    existing.reason_trace = list(action.reason_trace)
                    existing.severity = severity
                    existing.refreshed_at = datetime.now(timezone.utc)
                    self._origins[existing.request_id] = action
                return existing.model_copy(deep=True)
        pending = PendingApproval(
            request_id=uuid4().hex[:12],
            zone_id=zone_id,
            intervention=action.intervention,
            requested_at=datetime.now(timezone.utc),
            reason_trace=list(action.reason_trace),
            severity=severity,
            status="pending",
        )
        self._requests[pending.request_id] = pending
        self._origins[pending.request_id] = action
        return pending.model_copy(deep=True)

    def decide(self, request_id: str, approver: str, approve: bool) -> ActionRecord:
        """Append the decision as a new audit record and close the request."""
        pending = self._require(request_id)
        if pending.status != "pending":
            raise ValueError(f"request already decided: {request_id}")
        if not (approver or "").strip():
            raise ValueError("a decision needs a named approver")
        decision = "approved" if approve else "declined"
        trace = list(pending.reason_trace) + [
            f"source_action_id={self._origins[request_id].action_id}",
            f"requested_at={pending.requested_at.isoformat()}",
            f"decision={decision}",
        ]
        if not approve:
            trace.append(f"declined_by={approver}")
        record = ActionRecord(
            action_id=uuid4().hex[:12],
            intervention=pending.intervention,
            status="executed" if approve else "refused",
            at=datetime.now(timezone.utc),
            approved_by=approver if approve else None,
            reason_trace=trace,
        )
        self.audit.append(record)
        pending.status = decision
        pending.decided_by = approver
        pending.decided_at = record.at
        return record

    def pending(self) -> list[PendingApproval]:
        """Requests still awaiting a decision, in the order they were opened."""
        return [r.model_copy(deep=True)
                for r in self._requests.values() if r.status == "pending"]

    def get(self, request_id: str) -> PendingApproval:
        """A copy of the request: callers cannot mutate the queue's own state."""
        return self._require(request_id).model_copy(deep=True)

    def _require(self, request_id: str) -> PendingApproval:
        try:
            return self._requests[request_id]
        except KeyError:
            raise KeyError(f"unknown request_id: {request_id}") from None
