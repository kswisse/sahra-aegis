"""Golden audit transcripts: the refactor guardrail.

Captured from the working tree before the agent-kernel refactor. Any change to a
decision, an ordering, or a trace string shows up here as a diff. Regenerate only
with ``SAHRA_UPDATE_GOLDEN=1`` and review the diff line by line first.
"""

import json
import os
from pathlib import Path

import pytest

from sahra.audit import AuditLog
from sahra.demo import run_demo
from sahra.gate import ApprovalGate
from sahra.hitl import ApprovalQueue
from sahra.supervisor import run_day
from sahra.types import PopulationGroup

GOLDEN = Path(__file__).parent / "golden"
DATA = Path(__file__).resolve().parents[1] / "data"
UPDATE = os.environ.get("SAHRA_UPDATE_GOLDEN") == "1"

DAYS = {
    "day_2026-07-01": ("dubai_hourly_2026-07-01.json", "dubai-2026-07-01"),
    "day_2026-08-13": ("dubai_hourly_2026-08-13.json", "dubai-2026-08-13"),
}


def _normalise(records):
    """Replace only genuinely nondeterministic values, keeping every field.

    ``action_id`` is minted fresh per run and the approval record is stamped with
    wall-clock time. Both are replaced by stable tokens; nothing is dropped.
    """
    raw_ids = []
    for record in records:
        if record.action_id not in raw_ids:
            raw_ids.append(record.action_id)
    tokens = {raw: f"<action_id:{i}>" for i, raw in enumerate(raw_ids)}

    raw_requests = []
    for record in records:
        for item in record.reason_trace:
            if item.startswith("linked_request="):
                request_id = item.split("=", 1)[1]
                if request_id not in raw_requests:
                    raw_requests.append(request_id)
    request_tokens = {
        raw: f"<request_id:{i}>" for i, raw in enumerate(raw_requests)}

    normalised = []
    for record in records:
        row = json.loads(record.model_dump_json())
        row["action_id"] = tokens[row["action_id"]]
        trace = []
        for item in row["reason_trace"]:
            for raw, token in tokens.items():
                item = item.replace(raw, token)
            for raw, token in request_tokens.items():
                item = item.replace(raw, token)
            if item.startswith("requested_at="):
                item = "requested_at=<ts>"
            trace.append(item)
        row["reason_trace"] = trace
        if any(item.startswith("decision=") for item in trace):
            row["at"] = "<decision-at>"
        normalised.append(row)
    return normalised


def _scenario(name, tmp_path):
    if name == "demo":
        run_demo(tmp_path)
        return AuditLog(tmp_path / "audit.jsonl").read_all()

    fixture, zone = DAYS[name]
    audit = AuditLog(tmp_path / "audit.jsonl")
    queue = ApprovalQueue(audit)
    run_day(zone, PopulationGroup.SCHOOL, DATA / fixture,
            ApprovalGate(), audit, queue)
    for pending in queue.pending():
        queue.decide(pending.request_id, "reviewer@dxbops", approve=True)
    return audit.read_all()


@pytest.mark.parametrize("name", sorted(["demo", *DAYS]))
def test_golden_transcript(name, tmp_path):
    actual = _normalise(_scenario(name, tmp_path))
    path = GOLDEN / f"{name}.jsonl"

    if UPDATE:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
                    for row in actual),
            encoding="utf-8",
        )
        pytest.skip(f"golden rewritten: {path.name}")

    expected = [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(actual) == len(expected), (
        f"{name}: {len(actual)} records, golden has {len(expected)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        assert got == want, (
            f"{name}: record {index} differs\n got: {got}\nwant: {want}")
