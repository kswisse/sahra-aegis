import pytest
from sahra.gate import ApprovalGate, ApprovalRequired
from sahra.types import Intervention, InterventionKind


def i(consequential):
    return Intervention(kind=InterventionKind.ESCALATE, reason="r",
                        expected_risk_reduction=0.4, consequential=consequential)


def test_reversible_action_passes_without_an_approver():
    assert ApprovalGate().authorize(i(False), None) == i(False)


def test_consequential_action_without_an_approver_is_refused():
    with pytest.raises(ApprovalRequired):
        ApprovalGate().authorize(i(True), None)


def test_blank_approver_is_treated_as_absent():
    with pytest.raises(ApprovalRequired):
        ApprovalGate().authorize(i(True), "")


def test_consequential_action_passes_with_an_approver():
    result = ApprovalGate().authorize(i(True), "coordinator@schooldxb")
    assert result.consequential is True
