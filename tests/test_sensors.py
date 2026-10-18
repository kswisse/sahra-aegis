from datetime import datetime, timezone
import pytest
from sahra.sensors.satellite import SatelliteProvider
from sahra.sensors.site import SiteProvider
from sahra.sensors.weather import WeatherProvider

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)


def test_weather_provider_returns_a_typed_reading():
    p = WeatherProvider({"school-dxb-001": {"air_temp_c": 44.0, "humidity_pct": 70.0}})
    r = p.sample("school-dxb-001", AT)
    assert r.air_temp_c == 44.0 and r.humidity_pct == 70.0


def test_weather_provider_computes_the_outdoor_index_when_solar_is_present():
    p = WeatherProvider({"site-dxb-014": {
        "air_temp_c": 45.0, "humidity_pct": 10.0,
        "solar_wm2": 1000.0, "wind_ms": 1.0, "cos_zenith": 0.95,
    }})
    r = p.sample("site-dxb-014", AT)
    assert r.wbgt_c == pytest.approx(31.7, abs=0.3)
    assert r.solar_wm2 == 1000.0


def test_weather_provider_leaves_the_index_unset_without_solar():
    p = WeatherProvider({"school-dxb-001": {"air_temp_c": 44.0, "humidity_pct": 70.0}})
    assert p.sample("school-dxb-001", AT).wbgt_c is None


def test_site_provider_returns_none_for_a_zone_with_no_sensor():
    assert SiteProvider({"school-dxb-001": {"wbgt_c": 31.5}}).sample("school-dxb-999") is None


def test_site_provider_returns_the_sensor_value_when_present():
    assert SiteProvider({"school-dxb-001": {"wbgt_c": 31.5}}).sample("school-dxb-001").wbgt_c == 31.5


def test_satellite_provider_degrades_to_none_when_offline():
    assert SatelliteProvider(fixtures={}, online=False).lst_for("school-dxb-001") is None


def test_satellite_provider_uses_the_fixture_when_offline():
    p = SatelliteProvider(fixtures={"school-dxb-001": 48.2}, online=False)
    assert p.lst_for("school-dxb-001").lst_c == 48.2
