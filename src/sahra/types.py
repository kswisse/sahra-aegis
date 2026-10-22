from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PopulationGroup(str, Enum):
    SCHOOL = "school"
    OUTDOOR_WORKER = "outdoor_worker"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class InterventionKind(str, Enum):
    ADVISE = "advise"
    SHIFT_ACTIVITY = "shift_activity"
    ACTIVATE_COOLING = "activate_cooling"
    ESCALATE = "escalate"


class SatelliteReading(BaseModel):
    lst_c: float = Field(ge=-20, le=90)


class WeatherReading(BaseModel):
    air_temp_c: float = Field(ge=-20, le=70)
    humidity_pct: float = Field(ge=0, le=100)
    wbgt_c: float | None = Field(default=None, ge=-20, le=70)        # outdoor index, when the provider can derive it
    solar_wm2: float | None = Field(default=None, ge=0, le=1400)     # the irradiance that produced that index


class SiteReading(BaseModel):
    wbgt_c: float = Field(ge=-20, le=70)


class HeatState(BaseModel):
    zone_id: str
    at: datetime
    air_temp_c: float = Field(ge=-20, le=70)
    humidity_pct: float = Field(ge=0, le=100)
    wbgt_c: float | None = Field(default=None, ge=-20, le=70)
    lst_c: float | None = Field(default=None, ge=-20, le=90)
    source_tier: Literal["site", "weather-outdoor", "weather"]
    disagreement: str | None = None


class RiskAssessment(BaseModel):
    zone_id: str
    at: datetime
    group: PopulationGroup
    wbgt_c: float
    score: float = Field(ge=0, le=1)
    level: RiskLevel


class Intervention(BaseModel):
    kind: InterventionKind
    reason: str
    expected_risk_reduction: float = Field(ge=0, le=1)
    consequential: bool = False


class ActionRecord(BaseModel):
    action_id: str
    intervention: Intervention
    status: Literal["executed", "refused"]
    at: datetime
    approved_by: str | None = None
    reason_trace: list[str]


class CycleResult(BaseModel):
    state: HeatState
    assessment: RiskAssessment
    interventions: list[Intervention]
    actions: list[ActionRecord]
