"""Print one SAHRA cycle as the message exchange a judge can read.

Deterministic and offline: the readings below are the committed demo conflict
(shaded site sensor 29.0 C under a weather tier deriving 31.1 C), so the
dispute and the ruling really happen. No LLM and no network take part.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from sahra.audit import AuditLog
from sahra.gate import ApprovalGate
from sahra.kernel import run_cycle
from sahra.protocol import MessageKind
from sahra.types import PopulationGroup, SatelliteReading, SiteReading, WeatherReading

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)
ZONE = "school-dxb-003"
DEFAULT_AUDIT = ROOT / "sahra-demo-out" / "agent-transcript-audit.jsonl"


def _summary(message) -> str:
    payload = message.payload
    if message.kind is MessageKind.OBSERVATION:
        return (f"{payload.state.zone_id} at {payload.state.at:%Y-%m-%d %H:%M} UTC; "
                f"wbgt {payload.state.wbgt_c} C from {payload.state.source_tier}")
    if message.kind is MessageKind.DISPUTE:
        readings = " vs ".join(
            f"{reading.source} {reading.value_c} C" for reading in payload.readings)
        return f"{payload.topic}: {readings} (gap above {payload.threshold_c} C)"
    if message.kind is MessageKind.RULING:
        return f"{payload.policy}: {payload.reasoning}"
    if message.kind is MessageKind.ASSESSMENT:
        return (f"wbgt {payload.assessment.wbgt_c} C; "
                f"level={payload.assessment.level.value}; "
                f"score={payload.assessment.score}")
    if message.kind is MessageKind.PROPOSAL:
        return f"{len(payload.interventions)} interventions: " + ", ".join(
            intervention.kind.value for intervention in payload.interventions)
    if message.kind is MessageKind.DECISION:
        return f"{len(payload.actions)} actions: " + ", ".join(
            f"{action.intervention.kind.value}={action.status}"
            for action in payload.actions)
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    args = parser.parse_args()

    result = run_cycle(
        zone_id=ZONE, group=PopulationGroup.SCHOOL, at=AT,
        satellite=SatelliteReading(lst_c=57.0),
        weather=WeatherReading(air_temp_c=39.0, humidity_pct=35.0, wbgt_c=31.1),
        site=SiteReading(wbgt_c=29.0),
        gate=ApprovalGate(), audit=AuditLog(args.audit),
    )

    print(f"SAHRA agent transcript - {ZONE} - {AT:%Y-%m-%d %H:%M} UTC")
    print(f"audit: {args.audit}\n")
    for message in result.transcript:
        print(f"{message.sender.value:<7} -> {message.recipient.value:<7} : "
              f"{message.kind.value:<11} : {_summary(message)}")

    ruling = next(
        (message for message in result.transcript
         if message.kind is MessageKind.RULING), None)
    print()
    print(f"ruling: {ruling.payload.reasoning}" if ruling else "ruling: none")
    verification = result.verification
    verdict = "ok" if verification and verification.ok else "FAILED"
    print(f"verify: {verdict}")
    for finding in verification.findings if verification else ["no verification"]:
        print(f"  finding: {finding}")


if __name__ == "__main__":
    main()
