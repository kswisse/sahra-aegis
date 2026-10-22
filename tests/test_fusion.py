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
    assert s.disagreement is None


def test_a_disagreement_over_one_degree_takes_the_higher_index():
    wx = WeatherReading(air_temp_c=39.0, humidity_pct=35.0, wbgt_c=31.1, solar_wm2=500.0)
    s = fuse("school-dxb-003", AT, None, wx, SiteReading(wbgt_c=29.0))
    assert s.wbgt_c == 31.1
    assert s.source_tier == "weather-outdoor"
    assert "29.0" in s.disagreement and "31.1" in s.disagreement
    assert "conservative" in s.disagreement


def test_the_higher_site_reading_keeps_the_site_tier():
    wx = WeatherReading(air_temp_c=41.0, humidity_pct=62.0, wbgt_c=30.0)
    s = fuse("school-dxb-001", AT, None, wx, SiteReading(wbgt_c=31.5))
    assert s.wbgt_c == 31.5
    assert s.source_tier == "site"
    assert "30.0" in s.disagreement and "31.5" in s.disagreement


def test_a_gap_of_at_most_one_degree_keeps_the_site_sensor():
    wx = WeatherReading(air_temp_c=41.0, humidity_pct=62.0, wbgt_c=32.3)
    s = fuse("school-dxb-001", AT, None, wx, SiteReading(wbgt_c=31.5))
    assert s.wbgt_c == 31.5
    assert s.source_tier == "site"
    assert s.disagreement is None


def test_a_satellite_lst_far_above_air_is_labelled_advisory():
    wx = WeatherReading(air_temp_c=41.0, humidity_pct=62.0)
    s = fuse("school-dxb-001", AT, SatelliteReading(lst_c=60.0), wx, None)
    assert s.wbgt_c is None
    assert s.source_tier == "weather"
    assert "advisory only" in s.disagreement
    assert "60.0" in s.disagreement and "41.0" in s.disagreement


def test_satellite_never_changes_the_chosen_decision_value():
    wx = WeatherReading(air_temp_c=39.0, humidity_pct=35.0, wbgt_c=31.1)
    s = fuse("school-dxb-003", AT, SatelliteReading(lst_c=80.0), wx, SiteReading(wbgt_c=29.0))
    assert s.wbgt_c == 31.1
    assert s.source_tier == "weather-outdoor"
    assert s.lst_c == 80.0
