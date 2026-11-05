import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
WEB_DIR = ROOT / "web"
for p in (ROOT, SRC_DIR, WEB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.app import (
    get_status,
    get_zones,
    get_fixtures,
    simulate_cycle,
    simulate_day,
    get_hitl_queue,
    decide_hitl,
    get_audit,
    calculate_risk,
    get_replay,
    CycleRequest,
    DaySimRequest,
    DecideRequest,
    CalculateRequest,
)


def test_status_endpoint():
    status = get_status()
    assert status["status"] == "online"
    assert "SAHRA AEGIS" in status["engine"]
    assert len(status["roles"]) == 6


def test_zones_endpoint():
    zones = get_zones()
    assert len(zones) >= 4
    zone_ids = [z["id"] for z in zones]
    assert "dubai-2026-08-13" in zone_ids
    assert "school-dxb-001" in zone_ids


def test_fixtures_endpoint():
    fixtures = get_fixtures()
    assert len(fixtures) >= 2
    filenames = [f["filename"] for f in fixtures]
    assert "dubai_hourly_2026-08-13.json" in filenames


def test_simulate_cycle_normal():
    req = CycleRequest(
        zone_id="test-zone",
        group="school",
        air_temp_c=35.0,
        humidity_pct=40.0,
        solar_wm2=700.0,
        wind_ms=2.0,
    )
    result = simulate_cycle(req)
    assert result["zone_id"] == "test-zone"
    assert result["assessment"]["level"] in ("low", "moderate", "high", "extreme")
    assert len(result["actions"]) > 0
    assert len(result["transcript"]) > 0


def test_simulate_cycle_dispute():
    # Site reads 29.0 while weather reads much higher (~32-34) -> gap > 1.0 -> Arbiter triggers
    req = CycleRequest(
        zone_id="school-dxb-003",
        group="school",
        air_temp_c=42.0,
        humidity_pct=65.0,
        solar_wm2=900.0,
        wind_ms=2.0,
        site_wbgt_c=29.0,
    )
    result = simulate_cycle(req)
    assert result["dispute_detected"] is True
    assert result["ruling"] is not None
    assert result["ruling"]["policy"] == "conservative-max"


def test_simulate_day():
    req = DaySimRequest(
        fixture_filename="dubai_hourly_2026-08-13.json",
        group="school",
    )
    result = simulate_day(req)
    assert result["peak_wbgt_c"] == 34.5
    assert len(result["steps"]) == 24
    assert result["pending_count"] >= 1


def test_hitl_queue_and_decision():
    # Run a high heat cycle that triggers consequential ESCALATE without approver
    req = CycleRequest(
        zone_id="hitl-test-zone",
        group="outdoor_worker",
        air_temp_c=46.0,
        humidity_pct=75.0,
        solar_wm2=1000.0,
        wind_ms=1.0,
    )
    cycle_res = simulate_cycle(req)
    refused = [a for a in cycle_res["actions"] if a["status"] == "refused"]
    assert len(refused) > 0

    # Check queue
    queue = get_hitl_queue()
    assert len(queue) > 0
    target = queue[0]

    # Decide request
    dec_req = DecideRequest(
        request_id=target["request_id"],
        approver="coordinator@dxbops",
        approve=True,
    )
    decision = decide_hitl(dec_req)
    assert decision["status"] == "executed"
    assert decision["approved_by"] == "coordinator@dxbops"


def test_calculate_risk():
    req = CalculateRequest(
        air_temp_c=45.0,
        humidity_pct=60.0,
        solar_wm2=900.0,
        wind_ms=2.0,
        group="outdoor_worker",
    )
    calc = calculate_risk(req)
    assert calc["wbgt_outdoor_c"] > calc["wbgt_fallback_c"]
    assert calc["risk_level"] == "extreme"


def test_replay_benchmark():
    replay = get_replay()
    assert replay["total_days"] == 6
    assert len(replay["days"]) == 6
