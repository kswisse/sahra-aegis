# tests/test_risk.py
from datetime import datetime, timezone
import pytest
from sahra.risk import approx_wbgt_c, assess, globe_temp_c, wbgt_outdoor_c
from sahra.types import HeatState, PopulationGroup, RiskLevel

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def state(air, rh, wbgt=None):
    return HeatState(zone_id="z1", at=AT, air_temp_c=air, humidity_pct=rh,
                     wbgt_c=wbgt, source_tier="site" if wbgt else "weather")


def test_approx_wbgt_on_a_moderate_day_stays_below_threshold():
    assert approx_wbgt_c(30.0, 50.0) == pytest.approx(24.6, abs=0.4)


def test_approx_wbgt_on_a_dangerous_day_clears_the_high_band():
    assert approx_wbgt_c(35.0, 70.0) == pytest.approx(31.7, abs=0.4)


def test_approx_wbgt_is_monotonic_in_temperature():
    assert approx_wbgt_c(38.0, 60.0) > approx_wbgt_c(33.0, 60.0)


def test_site_sensor_value_is_used_verbatim():
    a = assess(state(45.0, 90.0, wbgt=29.0), PopulationGroup.SCHOOL)
    assert a.wbgt_c == 29.0 and a.level == RiskLevel.MODERATE


@pytest.mark.parametrize("wbgt,expected", [
    (27.9, RiskLevel.LOW),
    (28.0, RiskLevel.MODERATE),
    (30.0, RiskLevel.HIGH),
    (32.0, RiskLevel.EXTREME),
])
def test_band_boundaries(wbgt, expected):
    assert assess(state(40.0, 60.0, wbgt=wbgt), PopulationGroup.SCHOOL).level == expected


def test_workers_score_at_least_as_high_as_schools():
    school = assess(state(40.0, 60.0, wbgt=31.0), PopulationGroup.SCHOOL)
    worker = assess(state(40.0, 60.0, wbgt=31.0), PopulationGroup.OUTDOOR_WORKER)
    assert worker.score >= school.score and worker.score <= 1.0


def test_outdoor_wbgt_beats_the_no_solar_fallback_in_the_sun():
    assert wbgt_outdoor_c(45.0, 10.0, 1000.0, 1.0, 0.95) == pytest.approx(31.7, abs=0.3)
    assert approx_wbgt_c(45.0, 10.0) < 29.0


def test_outdoor_wbgt_collapses_to_the_fallback_without_solar():
    assert wbgt_outdoor_c(42.0, 40.0, 0.0, 2.0, 0.90) == pytest.approx(
        approx_wbgt_c(42.0, 40.0), abs=0.05)


def test_outdoor_wbgt_rises_with_solar_and_falls_with_wind():
    assert wbgt_outdoor_c(42.0, 40.0, 900.0, 2.0, 0.9) > wbgt_outdoor_c(42.0, 40.0, 300.0, 2.0, 0.9)
    assert wbgt_outdoor_c(42.0, 40.0, 900.0, 1.0, 0.9) > wbgt_outdoor_c(42.0, 40.0, 900.0, 5.0, 0.9)


def test_negative_irradiance_is_clamped_to_zero_and_never_cools_the_globe():
    """A negative irradiance is a data error, not a cooling effect."""
    assert globe_temp_c(42.0, -500.0, 2.0, 0.90) == globe_temp_c(42.0, 0.0, 2.0, 0.90)
    assert globe_temp_c(42.0, -500.0, 2.0, 0.90) >= 42.0
    assert wbgt_outdoor_c(42.0, 40.0, -500.0, 2.0, 0.90) == wbgt_outdoor_c(42.0, 40.0, 0.0, 2.0, 0.90)


def test_the_solar_term_can_raise_the_band_above_the_fallback():
    sunny = state(45.0, 10.0, wbgt=wbgt_outdoor_c(45.0, 10.0, 1000.0, 1.0, 0.95))
    fallback = state(45.0, 10.0)
    assert assess(sunny, PopulationGroup.OUTDOOR_WORKER).level is RiskLevel.HIGH
    assert assess(fallback, PopulationGroup.OUTDOOR_WORKER).level is RiskLevel.MODERATE
