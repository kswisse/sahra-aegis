import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure root & src are on sys.path
ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
WEB_DIR = ROOT / "web"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from backend import services
from sahra.types import PopulationGroup

app = FastAPI(
    title="SAHRA AEGIS Operations API",
    description="Rules-based multi-agent heat-stress decision engine for Dubai (Create AI Agents Championship)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = datetime.now(timezone.utc)

# ----------------- Request / Response Models -----------------

class CycleRequest(BaseModel):
    zone_id: str = "dubai-live"
    group: str = "school"  # "school" or "outdoor_worker"
    air_temp_c: float = Field(..., ge=-10, le=60)
    humidity_pct: float = Field(..., ge=0, le=100)
    solar_wm2: float = Field(default=800.0, ge=0, le=1400)
    wind_ms: float = Field(default=2.0, ge=0, le=50)
    site_wbgt_c: Optional[float] = Field(default=None, ge=-10, le=60)
    satellite_lst_c: Optional[float] = Field(default=None, ge=-10, le=90)
    approved_by: Optional[str] = None

class DaySimRequest(BaseModel):
    fixture_filename: str = "dubai_hourly_2026-08-13.json"
    zone_id: Optional[str] = None
    group: str = "school"

class DecideRequest(BaseModel):
    request_id: str
    approver: str = Field(..., min_length=2)
    approve: bool = True

class CalculateRequest(BaseModel):
    air_temp_c: float = 40.0
    humidity_pct: float = 50.0
    solar_wm2: float = 800.0
    wind_ms: float = 2.0
    group: str = "outdoor_worker"
    sun_elev_deg: float = 60.0

# ----------------- API Endpoints -----------------

@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    return {
        "status": "online",
        "engine": "SAHRA AEGIS Deterministic Decision Core",
        "version": "1.0.0",
        "architecture": "Deterministic Multi-Agent State Machine (0% LLM in Decision Path)",
        "uptime_seconds": int((now_utc - START_TIME).total_seconds()),
        "roles": [
            {"role": "Monitor", "responsibility": "Sensor Fusion (Weather tier, IoT Site Station, Satellite LST)"},
            {"role": "Predict", "responsibility": "WBGT Calculation (ISO 7243 Dimiceli Globe / Stull fallback) & Dispute Raising"},
            {"role": "Arbiter", "responsibility": "Conflict Resolution (Conservative-Max policy when gap > 1.0°C)"},
            {"role": "Plan", "responsibility": "Evidence-linked Intervention Mapping (Advise, Shift, Cooling, Escalate)"},
            {"role": "Act", "responsibility": "Approval Gate Guardrail (Refuses consequential actions without approver)"},
            {"role": "Verify", "responsibility": "Post-cycle Invariant Verification (Safe downgrade check, single ruling, unique IDs)"},
        ],
        "compliance": {
            "standard": "ISO 7243 / MOHRE UAE Heat Safety Regulations",
            "threshold_wbgt_c": 28.0,
            "extreme_threshold_wbgt_c": 32.0,
        },
        "pending_approvals_count": len(services.get_pending_queue()),
    }

@app.get("/api/zones")
def get_zones() -> List[Dict[str, Any]]:
    return services.PRESET_ZONES

@app.get("/api/fixtures")
def get_fixtures() -> List[Dict[str, Any]]:
    return services.get_fixtures_metadata()

@app.post("/api/simulate/cycle")
def simulate_cycle(req: CycleRequest) -> Dict[str, Any]:
    try:
        grp = PopulationGroup.SCHOOL if req.group == "school" else PopulationGroup.OUTDOOR_WORKER
        return services.execute_single_cycle(
            zone_id=req.zone_id,
            group=grp,
            air_temp_c=req.air_temp_c,
            humidity_pct=req.humidity_pct,
            solar_wm2=req.solar_wm2,
            wind_ms=req.wind_ms,
            site_wbgt_c=req.site_wbgt_c,
            satellite_lst_c=req.satellite_lst_c,
            approved_by=req.approved_by,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/simulate/day")
def simulate_day(req: DaySimRequest) -> Dict[str, Any]:
    try:
        grp = PopulationGroup.SCHOOL if req.group == "school" else PopulationGroup.OUTDOOR_WORKER
        return services.execute_day_simulation(
            fixture_filename=req.fixture_filename,
            zone_id=req.zone_id,
            group=grp,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/hitl/queue")
def get_hitl_queue() -> List[Dict[str, Any]]:
    return services.get_pending_queue()

@app.post("/api/hitl/decide")
def decide_hitl(req: DecideRequest) -> Dict[str, Any]:
    try:
        return services.decide_queue_request(
            request_id=req.request_id,
            approver=req.approver,
            approve=req.approve,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Request ID '{req.request_id}' not found in pending queue.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/audit")
def get_audit(
    limit: int = Query(default=100, ge=1, le=500),
    status: Optional[str] = Query(default="all"),
) -> List[Dict[str, Any]]:
    return services.get_audit_trail(limit=limit, status_filter=status)

@app.get("/api/audit/download")
def download_audit():
    audit_file = services.AUDIT_FILE
    if not audit_file.exists():
        return JSONResponse(status_code=404, content={"message": "No audit file generated yet."})
    return FileResponse(
        path=str(audit_file),
        media_type="application/x-jsonlines",
        filename="sahra-audit-log.jsonl",
    )

@app.post("/api/calculate")
def calculate_risk(req: CalculateRequest) -> Dict[str, Any]:
    grp = PopulationGroup.SCHOOL if req.group == "school" else PopulationGroup.OUTDOOR_WORKER
    return services.calculate_physics_wbgt(
        air_temp_c=req.air_temp_c,
        humidity_pct=req.humidity_pct,
        solar_wm2=req.solar_wm2,
        wind_ms=req.wind_ms,
        group=grp,
        sun_elev_deg=req.sun_elev_deg,
    )

@app.get("/api/replay")
def get_replay() -> Dict[str, Any]:
    return services.get_replay_benchmarks()

# ----------------- Static File Serving -----------------

STATIC_PATH = ROOT / "web" / "static"
if STATIC_PATH.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_PATH / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        content={
            "app": "SAHRA AEGIS Operations Web API",
            "message": "Frontend index.html is being prepared.",
            "docs": "/docs",
        }
    )
