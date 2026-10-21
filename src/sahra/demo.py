# src/sahra/demo.py
from datetime import datetime, timezone
from pathlib import Path

from .audit import AuditLog
from .channels.notify import render_advisory, render_operator_view
from .gate import ApprovalGate
from .orchestrator import run_cycle
from .sensors.satellite import SatelliteProvider
from .sensors.site import SiteProvider
from .sensors.weather import WeatherProvider
from .types import PopulationGroup

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)

WEATHER = {"school-dxb-001": {"air_temp_c": 44.0, "humidity_pct": 70.0},
           "site-dxb-014": {"air_temp_c": 45.0, "humidity_pct": 10.0,
                            "solar_wm2": 1000.0, "wind_ms": 1.0, "cos_zenith": 0.95}}
SITES = {"school-dxb-001": {"wbgt_c": 33.5}}  # site-dxb-014 has no sensor: it runs on the weather-outdoor tier
LST = {"school-dxb-001": 48.2, "site-dxb-014": 51.0}


def _verify(result) -> str:
    executed = sum(1 for a in result.actions if a.status == "executed")
    refused = sum(1 for a in result.actions if a.status == "refused")
    total = len(result.actions)
    counts = f"{executed} actions executed"
    if refused:
        counts += f", {refused} refused pending human approval"
    if executed + refused != total:
        counts += f", {total - executed - refused} in an unaccounted status"
    return (f"verify: {total} actions decided, {counts}; "
            f"claim limited to decision latency and action uptake, not health outcome")


def run_demo(tmp_dir: str | Path | None = None, approved_by: str | None = None) -> str:
    root = Path(tmp_dir) if tmp_dir else Path("sahra-demo-out")
    audit = AuditLog(root / "audit.jsonl")
    gate = ApprovalGate()
    wx, site = WeatherProvider(WEATHER), SiteProvider(SITES)
    sat = SatelliteProvider(LST, online=False)

    chunks = ["SAHRA live demonstration - Dubai, 14 July 2027, 13:00 local"]
    for zone_id, group in (("school-dxb-001", PopulationGroup.SCHOOL),
                           ("site-dxb-014", PopulationGroup.OUTDOOR_WORKER)):
        result = run_cycle(
            zone_id=zone_id, group=group, at=AT,
            satellite=sat.lst_for(zone_id), weather=wx.sample(zone_id, AT),
            site=site.sample(zone_id), gate=gate, audit=audit, approved_by=approved_by,
        )
        chunks += [render_advisory(result), render_operator_view(result), _verify(result)]
    return "\n\n".join(chunks)


if __name__ == "__main__":  # pragma: no cover
    print(run_demo())
