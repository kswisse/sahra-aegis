# tests/test_demo.py
from sahra.demo import run_demo


def test_demo_runs_a_hazardous_day_and_reports_the_verification_result(tmp_path):
    out = run_demo(tmp_path)
    assert "SAHRA" in out
    assert "school-dxb-001" in out
    assert "verify" in out.lower()
    assert "refused" in out.lower()


def test_demo_with_an_approver_executes_the_escalation(tmp_path):
    out = run_demo(tmp_path, approved_by="coordinator@schooldxb")
    assert "refused" not in out.lower()


def test_demo_writes_an_audit_file(tmp_path):
    run_demo(tmp_path)
    assert (tmp_path / "audit.jsonl").exists()


def test_demo_covers_both_population_groups(tmp_path):
    out = run_demo(tmp_path)
    assert "school" in out and "outdoor_worker" in out


def test_demo_reports_the_counts_instead_of_assuming_all_approved(tmp_path):
    out = run_demo(tmp_path)
    verify = [line for line in out.splitlines() if line.startswith("verify:")]
    assert len(verify) == 3
    assert "4 actions decided, 3 actions executed, 1 refused" in verify[0]
    assert "3 actions decided, 3 actions executed" in verify[1]
    assert "3 actions decided, 3 actions executed" in verify[2]
    assert "all approved" not in out.lower()


def test_demo_shows_the_tier_disagreement_resolved_conservatively(tmp_path):
    out = run_demo(tmp_path)
    assert "school-dxb-003" in out
    assert "Decision tier: weather-outdoor" in out
    assert "site 29.0 C vs weather-outdoor 31.1 C" in out
    assert "chose the higher, conservative 31.1 C" in out
    assert "advisory only, never the sole basis" in out
    assert "disagreement=tiers disagree" in out
