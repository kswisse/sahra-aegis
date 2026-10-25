from collections.abc import Iterable

from .hitl import PendingApproval
from .types import InterventionKind, RiskAssessment, RiskLevel


class Blackboard:
    """What the agents of one zone remember between cycles.

    The supervisor syncs it from the approval queue after every hour, so Plan
    can tag a repeated refusal with the request that already covers it.
    """

    def __init__(self) -> None:
        self.open_request_ids: dict[tuple[str, InterventionKind], str] = {}
        self.refused_bands: dict[tuple[str, InterventionKind], set[RiskLevel]] = {}
        self.last_assessment: RiskAssessment | None = None

    def sync(self, pending: Iterable[PendingApproval]) -> None:
        self.open_request_ids = {
            (request.zone_id, request.intervention.kind): request.request_id
            for request in pending
        }

    def link_for(self, zone_id: str, kind: InterventionKind) -> str | None:
        return self.open_request_ids.get((zone_id, kind))

    def observe(self, assessment: RiskAssessment) -> None:
        self.last_assessment = assessment

    def record_refusal(
        self, zone_id: str, kind: InterventionKind, level: RiskLevel
    ) -> None:
        self.refused_bands.setdefault((zone_id, kind), set()).add(level)
