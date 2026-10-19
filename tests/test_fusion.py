from datetime import datetime, timezone
from sahra.fusion import fuse
from sahra.types import SatelliteReading, SiteReading, WeatherReading

AT = datetime(2027, 7, 14, 13, 0, tzinfo=timezone.utc)
WX = WeatherReading(air_temp_c=41.0, humidity_pct=62.0)


def test_site_sensor_supplies_the_decision_value():
    s = fuse("school-dxb-001", AT, SatelliteReading(lst_c=48.2), WX, SiteReading(wbgt_c=31.5))
    assert s.wbgt_c == 31.5
    assert s.source_tier == "site"
    assert s.lst_c == 48.2


def test_without_site_sensor_wbgt_is_unset_and_tier_is_weather():
    s = fuse("school-dxb-001", AT, SatelliteReading(lst_c=48.2), WX, None)
    assert s.wbgt_c is None
    assert s.source_tier == "weather"


def test_satellite_never_overrides_the_weather_tier():
    s = fuse("school-dxb-001", AT, SatelliteReading(lst_c=60.0), WX, None)
    assert s.wbgt_c is None
    assert s.source_tier == "weather"
    assert s.air_temp_c == 41.0
    assert s.humidity_pct == 62.0


def test_weather_tier_outdoor_index_is_used_when_no_site_sensor_exists():
    wx = WeatherReading(air_temp_c=44.0, humidity_pct=70.0, wbgt_c=41.8, solar_wm2=900.0)
    s = fuse("school-dxb-001", AT, None, wx, None)
    assert s.wbgt_c == 41.8
    assert s.source_tier == "weather-outdoor"
