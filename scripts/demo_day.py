"""Run one archived Dubai day through SAHRA and print what happened.

Offline and deterministic: the committed fixture fixes the day, and the
decision path is a typed state machine - no LLM and no network take part.

The default fixture is the extreme day, so the consequential path really runs:
the gate refuses the escalation for want of an approver, the refusal is
opened as a pending request, and the coordinator's approval is appended to
the same audit. The milder day is available behind --fixture and says so.
"""

import argparse
import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sahra.audit import AuditLog
from sahra.gate import ApprovalGate
from sahra.hitl import ApprovalQueue
from sahra.supervisor import run_day
from sahra.types import PopulationGroup

DEFAULT_FIXTURE = ROOT / "data" / "dubai_hourly_2026-08-13.json"
DEFAULT_AUDIT = ROOT / "sahra-demo-out" / "demo-day-audit.jsonl"
DEFAULT_APPROVER = "coordinator@dxbops"
TAIL_RECORDS = 8
EXTREME_WBGT_C = 32.0


def _paragraph(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(text, width=88, initial_indent=indent, subsequent_indent=indent)


def _shown(path: Path | str) -> str:
    """Show a path relative to the repo root when it lives inside it."""
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def _trace_value(record, key: str) -> str:
    """One value out of an action's reason trace, e.g. 'wbgt' -> '34.5'."""
    prefix = f"{key}="
    for item in record.reason_trace:
        if item.startswith(prefix):
            return item[len(prefix):]
    return "?"


def _peak_step(timeline):
    return next(step for step in timeline.steps if step.at == timeline.peak_at)


def _header(meta: dict, fixture: Path, timeline, audit_path: str) -> list[str]:
    lines = [
        "SAHRA day demo - one archived Dubai day, hour by hour",
        "",
        f"Fixture   : {_shown(fixture)}",
        f"Dataset   : {meta.get('dataset', 'unknown')}",
        f"Source    : {meta.get('source_url', 'unknown')}",
        f"Retrieved : {meta.get('retrieved_at', 'unknown')}",
        f"License   : {meta.get('license', 'unknown')}",
        f"Zone      : {timeline.zone_id}   Group: {timeline.group.value}   "
        f"Date: {timeline.date} (Asia/Dubai)",
        f"Audit log : {_shown(audit_path)}",
        "",
        "Provenance:",
    ]
    lines += _paragraph(meta.get("note", ""), "  ")
    return lines + [""]


def _table(timeline, air_temps: dict[str, float]) -> list[str]:
    lines = [f"  {'time':<6}{'airC':>6}{'WBGT':>7}  {'band':<9}{'dispatch':<32}status"]
    for step in timeline.steps:
        kinds = [kind.value for kind in step.dispatched_kinds]
        kinds += [kind.value for kind in step.active_kinds]
        dispatch = ", ".join(kind.value for kind in step.dispatched_kinds) or "-"
        status = ", ".join(f"{kind}={state}" for kind, state in zip(kinds, step.statuses))
        air = air_temps.get(step.at.isoformat(), float("nan"))
        lines.append(f"  {step.at.strftime('%H:%M'):<6}{air:6.1f}{step.wbgt_c:7.1f}  "
                     f"{step.level.value:<9}{dispatch:<32}{status}")
    return lines


def _escalation(timeline, queue: ApprovalQueue, records: list, approver: str) -> list[str]:
    """The refusal, the pending requests, and the coordinator's decision."""
    refusals = [record for record in records if record.status == "refused"]
    pendings = queue.pending()
    lines = ["", "Escalation and the human in the loop", "-" * 32]

    if not refusals:
        lines += _paragraph(
            f"No escalation was raised on this day: the peak was {timeline.peak_wbgt_c} C "
            f"({_peak_step(timeline).level.value}), below the {EXTREME_WBGT_C:g} C extreme "
            "threshold, so the consequential path never opened and nothing was waiting for "
            "approval. The day is still a full 24-hour run: advisory, activity shift and "
            "cooling were dispatched and executed as the band rose and fell.")
        return lines

    lines += _paragraph(
        f"The extreme band opened at {refusals[0].at.strftime('%H:%M')} local. ESCALATE is a "
        "consequential intervention, so with no approver on duty the approval gate REFUSED it - "
        "it was never silently downgraded. Every refusal was opened as a pending request, in "
        "the order it happened:")
    lines += [
        "",
        f"  {'request':<14}{'kind':<10}{'hour':<7}{'wbgt':<7}{'band':<9}status",
    ]
    for refusal, pending in zip(refusals, pendings):
        lines.append(f"  {pending.request_id:<14}{pending.intervention.kind.value:<10}"
                     f"{refusal.at.strftime('%H:%M'):<7}{_trace_value(refusal, 'wbgt'):<7}"
                     f"{_trace_value(refusal, 'level'):<9}{pending.status}")

    first = refusals[0]
    lines += [
        "",
        f"The refusal as written to the audit ({first.at.strftime('%H:%M')}):",
        f"  [{first.action_id}] {first.intervention.kind.value} -> {first.status} "
        f"(approved_by={first.approved_by})",
        f"      reason: {'; '.join(first.reason_trace)}",
    ]

    peak_refusal = next(refusal for refusal in refusals
                        if _trace_value(refusal, "wbgt") == str(timeline.peak_wbgt_c))
    pending = pendings[refusals.index(peak_refusal)]
    decision = queue.decide(pending.request_id, approver, approve=True)
    lines += [
        "",
        f"Coordinator decision on the peak-hour escalation "
        f"({peak_refusal.at.strftime('%H:%M')}, WBGT {timeline.peak_wbgt_c} C):",
        f"  request {pending.request_id} -> APPROVED by {approver}",
        f"  audit record appended: [{decision.action_id}] "
        f"{decision.intervention.kind.value} -> {decision.status} "
        f"(approved_by={decision.approved_by})",
        "  the refusal above is still in the audit, unchanged; the decision is a new record",
        "  (stamped with the time of this run, not the archived hour)",
    ]
    return lines


def _audit_tail(records: list) -> list[str]:
    tail = records[-TAIL_RECORDS:]
    lines = ["", f"Audit tail (last {len(tail)} of the {len(records)} records this run wrote; "
                  "the log is append-only):"]
    for record in tail:
        lines.append(f"  {record.at.strftime('%Y-%m-%d %H:%M')}  "
                     f"{record.intervention.kind.value:<18}-> {record.status:<9}"
                     f"(approved_by={record.approved_by})")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one archived Dubai day through SAHRA.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE),
                        help="committed hourly fixture (default: the extreme day)")
    parser.add_argument("--group", default=PopulationGroup.SCHOOL.value,
                        choices=[group.value for group in PopulationGroup],
                        help="population group the day is assessed for")
    parser.add_argument("--approver", default=DEFAULT_APPROVER,
                        help="the name that signs the coordinator's approval")
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT),
                        help="where the append-only audit log is written")
    args = parser.parse_args(argv)

    fixture = Path(args.fixture)
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    meta = payload["meta"]
    air_temps = {row["time"]: row["air_temp_c"] for row in payload["hours"]}

    audit = AuditLog(args.audit)
    queue = ApprovalQueue(audit)
    already = len(audit.read_all())
    timeline = run_day(meta["zone_id"], PopulationGroup(args.group), fixture,
                       ApprovalGate(), audit, queue)
    records = audit.read_all()[already:]

    lines = _header(meta, fixture, timeline, args.audit)
    lines += _table(timeline, air_temps)
    lines += ["", f"Peak WBGT {timeline.peak_wbgt_c} C at "
                  f"{timeline.peak_at.strftime('%H:%M')} local "
                  f"({_peak_step(timeline).level.value} band)."]
    lines += _escalation(timeline, queue, records, args.approver)
    lines += _audit_tail(audit.read_all()[already:])
    lines += [""]
    lines += _paragraph(
        "Scope: this run measures decision latency and action uptake, not health outcomes. "
        "The fixture is ERA5 reanalysis, not station observation - a coverage input for the "
        "engine, not evidence about people.")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
