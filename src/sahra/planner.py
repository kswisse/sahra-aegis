from .types import Intervention, InterventionKind, RiskAssessment, RiskLevel


def plan(assessment: RiskAssessment) -> list[Intervention]:
    wbgt = assessment.wbgt_c
    out = [
        Intervention(
            kind=InterventionKind.ADVISE,
            reason=f"WBGT {wbgt}C: issue heat advisory to zone supervisor",
            expected_risk_reduction=0.10,
        )
    ]
    if assessment.level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.EXTREME):
        out.append(Intervention(
            kind=InterventionKind.SHIFT_ACTIVITY,
            reason=f"WBGT {wbgt}C exceeds the 28C occupational threshold: propose shifting activity out of peak hours",
            expected_risk_reduction=0.35,
        ))
    if assessment.level in (RiskLevel.HIGH, RiskLevel.EXTREME):
        out.append(Intervention(
            kind=InterventionKind.ACTIVATE_COOLING,
            reason=f"WBGT {wbgt}C in the high band: activate shading/misting and hydration breaks",
            expected_risk_reduction=0.30,
        ))
    if assessment.level is RiskLevel.EXTREME:
        out.append(Intervention(
            kind=InterventionKind.ESCALATE,
            reason=f"WBGT {wbgt}C at the extreme band: escalate to the supervising authority",
            expected_risk_reduction=0.45,
            consequential=True,
        ))
    return sorted(out, key=lambda i: i.expected_risk_reduction, reverse=True)
