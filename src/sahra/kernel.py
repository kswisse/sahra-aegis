from datetime import datetime
from uuid import uuid4

from .agents import (
    ActAgent,
    ArbiterAgent,
    MonitorAgent,
    PlanAgent,
    PredictAgent,
    VerifyAgent,
)
from .audit import AuditLog
from .blackboard import Blackboard
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
    blackboard: Blackboard | None = None,
) -> CycleResult:
    """Deterministic control plane: sense -> assess -> plan -> gate -> act -> log.
    No LLM participates in any of these transitions."""
    board = blackboard if blackboard is not None else Blackboard()
    monitor = MonitorAgent()
    predict = PredictAgent(group)
    planner = PlanAgent(board)
    act = ActAgent(gate, audit, approved_by, board)
    verify = VerifyAgent()
    coordinator = AgentCoordinator({
        AgentRole.MONITOR: monitor,
        AgentRole.PREDICT: predict,
        AgentRole.PLAN: planner,
        AgentRole.ACT: act,
        AgentRole.VERIFY: verify,
        AgentRole.ARBITER: ArbiterAgent(),
    })

    seed = monitor.observe(zone_id, at, satellite, weather, site, uuid4().hex)
    coordinator.run([seed])
    verification = verify.last_result

    return CycleResult(
        state=predict.last_state,
        assessment=predict.last_assessment,
        interventions=planner.last_interventions,
        actions=act.last_actions,
        transcript=list(coordinator.transcript),
        verification=verification,
    )
