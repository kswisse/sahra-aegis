from ..types import CycleResult


def render_advisory(result: CycleResult) -> str:
    a = result.assessment
    lines = [
        f"SAHRA heat advisory - zone {a.zone_id}",
        f"Risk level: {a.level.value} (WBGT {a.wbgt_c}C, threshold 28C)",
        f"Population: {a.group.value}",
        "Recommended actions:",
    ]
    for action in result.actions:
        lines.append(f"  - {action.intervention.kind.value}: {action.intervention.reason}")
    return "\n".join(lines)


def render_operator_view(result: CycleResult) -> str:
    lines = [
        f"SAHRA operator view - {result.state.zone_id}",
        f"Decision tier: {result.state.source_tier}",
    ]
    for action in result.actions:
        lines.append(
            f"[{action.action_id}] {action.intervention.kind.value} -> {action.status}"
            + (f" (approved_by={action.approved_by})" if action.approved_by else "")
        )
        lines.append("    reason: " + "; ".join(action.reason_trace))
    return "\n".join(lines)
