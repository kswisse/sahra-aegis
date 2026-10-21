from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from sahra.types import (
    PopulationGroup, RiskLevel, InterventionKind,
    SatelliteReading, WeatherReading, SiteReading,
    HeatState, RiskAssessment, Intervention, ActionRecord,
)

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def test_heat_state_accepts_missing_optional_tiers():
    s = HeatState(zone_id="school-dxb-001", at=AT, air_temp_c=41.0,
                  humidity_pct=62.0, source_tier="weather")
    assert s.wbgt_c is None and s.lst_c is None


def test_humidity_is_bounded():
    with pytest.raises(ValidationError):
        HeatState(zone_id="z", at=AT, air_temp_c=30.0, humidity_pct=140.0,
                  source_tier="weather")


def test_risk_score_is_bounded():
    with pytest.raises(ValidationError):
        RiskAssessment(zone_id="z", at=AT, group=PopulationGroup.SCHOOL,
                       wbgt_c=30.0, score=1.5, level=RiskLevel.HIGH)


def test_enums_and_readings_construct():
    assert InterventionKind.ESCALATE.value == "escalate"
    assert PopulationGroup.OUTDOOR_WORKER.value == "outdoor_worker"
    assert SatelliteReading(lst_c=48.2).lst_c == 48.2
    assert WeatherReading(air_temp_c=41.0, humidity_pct=62.0).air_temp_c == 41.0
    assert SiteReading(wbgt_c=31.5).wbgt_c == 31.5


def test_weather_reading_carries_the_outdoor_index_and_solar_input():
    r = WeatherReading(air_temp_c=44.0, humidity_pct=70.0, wbgt_c=41.8, solar_wm2=900.0)
    assert r.wbgt_c == 41.8 and r.solar_wm2 == 900.0
    assert WeatherReading(air_temp_c=41.0, humidity_pct=62.0).wbgt_c is None


def test_source_tier_is_narrowed_to_the_three_tiers_the_engine_produces():
    with pytest.raises(ValidationError):
        HeatState(zone_id="z", at=AT, air_temp_c=30.0, humidity_pct=40.0,
                  source_tier="satellite")


def test_action_record_carries_reason_trace():
    i = Intervention(kind=InterventionKind.ADVISE, reason="wbgt 29.4 over 28 threshold",
                     expected_risk_reduction=0.2, consequential=False)
    r = ActionRecord(action_id="a1", intervention=i, status="executed",
                     at=AT, reason_trace=["wbgt=29.4 >= 28"])
    assert r.approved_by is None and r.reason_trace == ["wbgt=29.4 >= 28"]
