from datetime import datetime, timezone
from sahra.planner import plan
from sahra.types import InterventionKind, PopulationGroup, RiskAssessment, RiskLevel

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def a(wbgt, level, group=PopulationGroup.SCHOOL):
    return RiskAssessment(zone_id="z1", at=AT, group=group, wbgt_c=wbgt,
                          score=0.5, level=level)


def kinds(wbgt, level, group=PopulationGroup.SCHOOL):
    return [i.kind for i in plan(a(wbgt, level, group))]


def test_below_threshold_produces_advisory_only():
    assert kinds(26.5, RiskLevel.LOW) == [InterventionKind.ADVISE]


def test_moderate_adds_shift_activity_which_outranks_the_advisory():
    ks = kinds(29.0, RiskLevel.MODERATE)
    assert ks[0] == InterventionKind.SHIFT_ACTIVITY
    assert InterventionKind.ADVISE in ks


def test_extreme_adds_cooling_and_escalation():
    ks = kinds(33.0, RiskLevel.EXTREME)
    assert InterventionKind.ACTIVATE_COOLING in ks
    assert InterventionKind.ESCALATE in ks


def test_escalation_is_flagged_consequential():
    esc = [i for i in plan(a(33.0, RiskLevel.EXTREME)) if i.kind == InterventionKind.ESCALATE]
    assert esc and esc[0].consequential is True


def test_plan_is_sorted_by_expected_risk_reduction():
    reds = [i.expected_risk_reduction for i in plan(a(33.0, RiskLevel.EXTREME))]
    assert reds == sorted(reds, reverse=True)
