# tests/test_replay.py
import pytest
from sahra.replay import band, load_fixtures, render_table, validate
from sahra.types import RiskLevel


@pytest.fixture(scope="module")
def days():
    return load_fixtures()


def test_fixture_replays_offline(days):
    assert len(days) == 6
    assert {d.id for d in days} >= {"ncm-2025-05-24-sweihan-51.6C", "dubai-2026-07-01-mohre"}


def test_the_three_record_days_carry_their_official_temperature(days):
    records = [d for d in days if d.record_air_temp_c is not None]
    assert {d.record_air_temp_c for d in records} == {51.6, 46.6, 50.0}


def test_the_mohre_window_replays_as_high_or_worse(days):
    d = next(x for x in days if "mohre" in x.id)
    assert band(d) >= RiskLevel.HIGH


def test_the_mild_control_stays_low(days):
    d = next(x for x in days if "control" in x.id)
    assert band(d) == RiskLevel.LOW


def test_the_outdoor_form_beats_the_fallback_on_every_day(days):
    assert all(d.outdoor_wbgt_c() > d.fallback_wbgt_c() for d in days)


def test_a_hotter_drier_day_bands_below_a_cooler_humid_one(days):
    sweihan = next(x for x in days if x.id.startswith("ncm-2025-05-24"))
    humid = next(x for x in days if x.id.startswith("dubai-2026-08-05"))
    assert sweihan.air_temp_c > humid.air_temp_c
    assert sweihan.outdoor_wbgt_c() < humid.outdoor_wbgt_c()


def test_reanalysis_understates_the_station_peak(days):
    for d in (d for d in days if d.record_air_temp_c is not None):
        assert d.air_temp_c < d.record_air_temp_c


def test_validate_returns_every_claim(days):
    claims = validate(days)
    assert len(claims) == 5
    assert "MOHRE" in claims[0]


def test_the_table_has_a_row_per_day(days):
    assert len(render_table(days).splitlines()) == len(days) + 1
