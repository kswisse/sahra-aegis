# tests/test_replay.py
import pytest
import sahra.replay as replay
from sahra.replay import ReplayDay, band, load_fixtures, render_table, severity, validate
from sahra.types import RiskLevel


@pytest.fixture(scope="module")
def days():
    return load_fixtures()


def _day(day_id, air_temp_c, humidity_pct, solar_wm2=900.0, wind_ms=3.0,
         cos_zenith=0.99, direct_fraction=0.7):
    return ReplayDay(id=day_id, place="synthetic", date="2026-07-01",
                     air_temp_c=air_temp_c, humidity_pct=humidity_pct,
                     solar_wm2=solar_wm2, wind_ms=wind_ms,
                     cos_zenith=cos_zenith, direct_fraction=direct_fraction)


def test_fixture_replays_offline(days):
    assert len(days) == 6
    assert {d.id for d in days} >= {"ncm-2025-05-24-sweihan-51.6C", "dubai-2026-07-01-mohre"}


def test_the_three_record_days_carry_their_official_temperature(days):
    records = [d for d in days if d.record_air_temp_c is not None]
    assert {d.record_air_temp_c for d in records} == {51.6, 46.6, 50.0}


def test_the_mohre_window_replays_as_high_or_worse(days):
    d = next(x for x in days if "mohre" in x.id)
    assert band(d) in (RiskLevel.HIGH, RiskLevel.EXTREME)


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
    assert severity(band(sweihan)) < severity(band(humid))


def test_reanalysis_understates_the_station_peak(days):
    for d in (d for d in days if d.record_air_temp_c is not None):
        assert d.air_temp_c < d.record_air_temp_c


def test_validate_returns_every_claim(days):
    claims = validate(days)
    assert len(claims) == 5
    assert "MOHRE" in claims[0]


def test_the_table_has_a_row_per_day(days):
    assert len(render_table(days).splitlines()) == len(days) + 1


def test_a_mild_mohre_row_fails_validation(days):
    mild = _day("dubai-2026-01-01-mohre", air_temp_c=20.0, humidity_pct=30.0,
                solar_wm2=100.0)
    assert band(mild) == RiskLevel.LOW
    with pytest.raises(AssertionError):
        validate([mild])


def test_an_extreme_mohre_row_passes_validation(days):
    extreme = _day("dubai-2026-08-01-mohre-extreme", air_temp_c=40.0,
                   humidity_pct=40.0, solar_wm2=1000.0, wind_ms=1.0)
    assert band(extreme) == RiskLevel.EXTREME
    claims = validate([*days, extreme])
    assert "2 midday sample" in claims[0]


def test_validate_exits_zero_when_every_claim_holds(monkeypatch):
    monkeypatch.setattr(replay, "validate", lambda days: ["claim"])
    assert replay.main(["--validate"]) == 0


def test_validate_exits_non_zero_when_a_claim_fails(monkeypatch, capsys):
    def boom(days):
        raise AssertionError("MOHRE window sample bands lower")

    monkeypatch.setattr(replay, "validate", boom)
    assert replay.main(["--validate"]) == 1
    assert "MOHRE window sample bands lower" in capsys.readouterr().err
