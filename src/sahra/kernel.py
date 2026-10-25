from datetime import datetime
from uuid import uuid4

from .agents import ActAgent, MonitorAgent, PlanAgent, PredictAgent, VerifyAgent
from .audit import AuditLog
from .coordinator import AgentCoordinator
from .gate import ApprovalGate
from .protocol import AgentRole
from .types import (
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
    monitor = MonitorAgent()
    predict = PredictAgent(group)
    planner = PlanAgent()
    act = ActAgent(gate, audit, approved_by)
    verify = VerifyAgent()
    coordinator = AgentCoordinator({
        AgentRole.MONITOR: monitor,
        AgentRole.PREDICT: predict,
        AgentRole.PLAN: planner,
        AgentRole.ACT: act,
        AgentRole.VERIFY: verify,
    })

    seed = monitor.observe(zone_id, at, satellite, weather, site, uuid4().hex)
    coordinator.run([seed])

    return CycleResult(
        state=predict.last_state,
        assessment=predict.last_assessment,
        interventions=planner.last_interventions,
        actions=act.last_actions,
        transcript=list(coordinator.transcript),
        verification=None,
    )
