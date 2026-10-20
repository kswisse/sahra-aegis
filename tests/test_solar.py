from datetime import date, datetime, timedelta

import pytest

from sahra.solar import cos_zenith, sunrise_sunset


def test_sunrise_and_sunset_match_the_archive_within_three_minutes():
    sunrise, sunset = sunrise_sunset(25.202108, 55.302376, date(2026, 7, 1))
    assert abs((sunrise - datetime.fromisoformat("2026-07-01T05:32:00+04:00")).total_seconds()) <= 180
    assert abs((sunset - datetime.fromisoformat("2026-07-01T19:13:00+04:00")).total_seconds()) <= 180


def test_solar_noon_is_when_the_sun_is_highest_and_near_overhead():
    # minute resolution: the hour-long noon window is only reachable on a
    # sub-hourly grid (solar noon is ~12:22 local, not on the hour).
    start = datetime.fromisoformat("2026-07-01T00:00:00+04:00")
    day = [start + timedelta(minutes=m) for m in range(24 * 60)]
    noon = max(day, key=lambda t: cos_zenith(25.202108, 55.302376, t))
    assert datetime.fromisoformat("2026-07-01T12:05:00+04:00") <= noon <= datetime.fromisoformat("2026-07-01T12:30:00+04:00")
    # 0.999 is cos(latitude - solar declination) for that date, i.e. the sun overhead.
    assert cos_zenith(25.202108, 55.302376, noon) == pytest.approx(0.999, abs=0.005)


def test_zenith_is_negative_at_night():
    assert cos_zenith(25.202108, 55.302376, datetime.fromisoformat("2026-07-01T02:00:00+04:00")) < 0
