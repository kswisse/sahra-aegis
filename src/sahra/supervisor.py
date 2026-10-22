"""Day supervisor: one control cycle per hour over an archived day.

The audit stays the complete record — every action the engine took is appended
and nothing is filtered. The timeline is where readability lives: a kind
dispatched earlier in the day and proposed again in this same hour is listed
under `active_kinds` instead of being re-listed as a new dispatch, so a day
reads as a rising curve rather than 24 repetitions of the same advisory.
`active_kinds` is a display rule, not a deactivation: a kind leaves the
timeline at the hour the planner stops proposing it, because the band moved.

A consequential action refused for want of an approver is opened as a pending
request when an approval queue is supplied; the refusal itself stays in the
audit exactly as it was written. Each step keeps its actions as (kind, status)
pairs, so a kind and its outcome can never drift apart. No LLM and no network
take part.
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from .audit import AuditLog
from .gate import ApprovalGate
from .hitl import ApprovalQueue
from .orchestrator import run_cycle
from .sensors.weather import HourlyWeatherProvider
from .types import InterventionKind, PopulationGroup, RiskLevel


class HourlyStep(BaseModel):
    """One hour of the day, as the supervisor reads it.

    `dispatched_kinds` are the kinds this hour put on the table for the first
    time today; `active_kinds` are the kinds dispatched earlier today that the
    planner proposed again in this same hour. `statuses[i]` is the outcome of
    `(dispatched_kinds + active_kinds)[i]`, so the two kind lists and the
    statuses always pair up. `active_kinds` is a display rule, not a
    deactivation: a kind leaves the timeline at the hour the planner stops
    proposing it, because the band moved.
    """

    at: datetime
    wbgt_c: float
    level: RiskLevel
    dispatched_kinds: list[InterventionKind]
    active_kinds: list[InterventionKind]
    statuses: list[str]


class DayTimeline(BaseModel):
    """A whole day: the steps, the escalations awaiting a human, the peak.

    `peak_at` is the hour of the true maximum of the derived index, so hours
    that share the same displayed one-decimal value do not pick the wrong one.
    """

    zone_id: str
    group: PopulationGroup
    date: str
    steps: list[HourlyStep]
    pending_ids: list[str]
    peak_wbgt_c: float
    peak_at: datetime


def run_day(
    zone_id: str,
    group: PopulationGroup,
    fixture_path: Path | str,
    gate: ApprovalGate,
    audit: AuditLog,
    queue: ApprovalQueue | None = None,
) -> DayTimeline:
    """Run one cycle per hour over the fixture's hours, in order."""
    try:
        provider = HourlyWeatherProvider(fixture_path)
        hours = provider.hours(zone_id)
    except KeyError as exc:
        raise KeyError(f"fixture {fixture_path}: {exc}") from exc
    if not hours:
        raise ValueError(f"fixture {fixture_path} has no hours for zone {zone_id}")

    steps: list[HourlyStep] = []
    pending_ids: list[str] = []
    issued: set[InterventionKind] = set()
    peak_index: float | None = None
    peak_at = hours[0]

    for at in hours:
        try:
            weather = provider.sample(zone_id, at)
        except KeyError as exc:
            raise KeyError(f"fixture {fixture_path}: {exc}") from exc
        result = run_cycle(
            zone_id=zone_id, group=group, at=at, satellite=None, weather=weather,
            site=None, gate=gate, audit=audit,
        )
        pairs = [(action.intervention.kind, action.status) for action in result.actions]
        dispatched = [pair for pair in pairs if pair[0] not in issued]
        active = [pair for pair in pairs if pair[0] in issued]
        steps.append(HourlyStep(
            at=at,
            wbgt_c=result.assessment.wbgt_c,
            level=result.assessment.level,
            dispatched_kinds=[kind for kind, _ in dispatched],
            active_kinds=[kind for kind, _ in active],
            statuses=[status for _, status in dispatched + active],
        ))
        issued.update(kind for kind, _ in pairs)

        index = result.state.wbgt_c
        if peak_index is None or index > peak_index:
            peak_index, peak_at = index, at

        if queue is not None:
            for action in result.actions:
                if action.status == "refused" and action.intervention.consequential:
                    pending_ids.append(queue.request(action, zone_id).request_id)

    return DayTimeline(
        zone_id=zone_id,
        group=group,
        date=hours[0].date().isoformat(),
        steps=steps,
        pending_ids=pending_ids,
        peak_wbgt_c=round(peak_index, 1),
        peak_at=peak_at,
    )
