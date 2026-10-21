# tests/test_demo_day.py
"""Smoke test for the judge-facing day demo.

`scripts/demo_day.py` is the artefact a judge watches, so it gets a check of
its own: 24 hours of table, the extreme band, an escalation refused for want
of an approver, and the coordinator's approval appended to the same audit.
The run is offline and writes nothing into the repo tree.
"""
import json
import os
import re
import runpy
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "demo_day.py"
FIXTURE = ROOT / "data" / "dubai_hourly_2026-08-13.json"
APPROVER = "coordinator@dxbops"


def test_the_day_demo_runs_the_extreme_day_offline_and_leaves_no_trace(tmp_path, monkeypatch, capsys):
    def no_network(*args, **kwargs):
        raise AssertionError("the demo must not touch the network")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    before = set(os.listdir(ROOT))

    # run the script the way a judge does: as __main__, with the audit in tmp_path
    monkeypatch.setattr(sys, "argv", ["demo_day.py", "--fixture", str(FIXTURE),
                                      "--audit", str(tmp_path / "audit.jsonl")])
    with pytest.raises(SystemExit) as finished:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert finished.value.code == 0
    out = capsys.readouterr().out

    assert set(os.listdir(ROOT)) == before
    assert re.findall(r"^  (\d{2}:\d{2}) ", out, re.M) == [f"{hour:02d}:00" for hour in range(24)]
    assert re.search(r"Peak WBGT [\d.]+ C at \d{2}:\d{2} local \(extreme band\)", out)
    assert "escalate=refused" in out
    assert "escalate -> refused" in out
    assert f"APPROVED by {APPROVER}" in out
    assert "escalate -> executed" in out
    assert "ECMWF ERA5 reanalysis" in out
    assert "archive-api.open-meteo.com" in out

    records = [json.loads(line) for line in
               (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 69
    assert sum(1 for record in records if record["status"] == "refused") == 8
    assert records[0]["status"] == "executed"
    assert records[-1]["status"] == "executed"
    assert records[-1]["approved_by"] == APPROVER
    assert records[-1]["intervention"]["kind"] == "escalate"
