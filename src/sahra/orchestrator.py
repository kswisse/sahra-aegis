from datetime import datetime
from uuid import uuid4

from .audit import AuditLog
from .fusion import fuse
from .gate import ApprovalGate, ApprovalRequired
from .planner import plan
from .risk import THRESHOLD_C, assess
from .types import (
    ActionRecord,
    CycleResult,
    PopulationGroup,
    SatelliteReading,
    SiteReading,
    WeatherReading,
)


def run_cycle(
    zone_id: str,
    group: PopulationGroup,
    at: datetime,
    satellite: SatelliteReading | None,
    weather: WeatherReading,
    site: SiteReading | None,
    gate: ApprovalGate,
    audit: AuditLog,
    approved_by: str | None = None,
) -> CycleResult:
    """Deterministic control plane: sense -> assess -> plan -> gate -> act -> log.
    No LLM participates in any of these transitions."""
    state = fuse(zone_id, at, satellite, weather, site)
    assessment = assess(state, group)
    interventions = plan(assessment)

    actions: list[ActionRecord] = []
    for intervention in interventions:
        trace = [
            f"tier={state.source_tier}",
            f"wbgt={assessment.wbgt_c}",
            f"threshold={THRESHOLD_C}",
            f"level={assessment.level.value}",
            f"expected_risk_reduction={intervention.expected_risk_reduction}",
            f"zone={zone_id}",
        ]
        try:
            gate.authorize(intervention, approved_by)
            status, approver = "executed", approved_by
        except ApprovalRequired as exc:
            trace.append(f"gate_reason={exc}")
            status, approver = "refused", None
        record = ActionRecord(
            action_id=uuid4().hex[:12], intervention=intervention, status=status,
            at=at, approved_by=approver, reason_trace=trace,
        )
        audit.append(record)
        actions.append(record)

    return CycleResult(state=state, assessment=assessment,
                       interventions=interventions, actions=actions)
