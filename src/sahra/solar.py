"""Solar geometry for the Dubai site. NOAA solar-position math, pure and
offline: fractional year -> equation of time -> solar declination -> hour
angle -> zenith angle.

The site sits on Asia/Dubai (UTC+04:00, no DST), so the offset is fixed rather
than looked up. The functions take wall-clock times in that zone and return
times in the same zone.
"""

import math
from datetime import date, datetime, timedelta, timezone

UTC_OFFSET_HOURS = 4.0
LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))

_ZENITH_DEGREES = 90.833  # solar radius plus standard atmospheric refraction


def _fractional_year(day: date, hour: float) -> float:
    return 2 * math.pi / 365 * (day.timetuple().tm_yday - 1 + (hour - 12) / 24)


def _equation_of_time_minutes(gamma: float) -> float:
    return 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                     - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))


def _solar_declination_rad(gamma: float) -> float:
    return (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))


def _wall_clock(at_local: datetime) -> datetime:
    if at_local.tzinfo is None:
        return at_local
    return at_local.astimezone(LOCAL_TZ)


def cos_zenith(latitude_deg: float, longitude_deg: float, at_local: datetime) -> float:
    """Cosine of the solar zenith angle at that local time: 1 is the sun
    straight overhead, 0 is the horizon, negative means the sun is below it."""
    local = _wall_clock(at_local)
    gamma = _fractional_year(local.date(), local.hour + local.minute / 60 + local.second / 3600)
    offset = _equation_of_time_minutes(gamma) + 4 * longitude_deg - 60 * UTC_OFFSET_HOURS
    true_solar_minutes = local.hour * 60 + local.minute + local.second / 60 + offset
    hour_angle = math.radians(true_solar_minutes / 4 - 180)
    latitude = math.radians(latitude_deg)
    declination = _solar_declination_rad(gamma)
    return (math.sin(latitude) * math.sin(declination)
            + math.cos(latitude) * math.cos(declination) * math.cos(hour_angle))


def sunrise_sunset(latitude_deg: float, longitude_deg: float,
                   date_local: date) -> tuple[datetime, datetime]:
    """Sunrise and sunset for that local date, as Asia/Dubai wall-clock times."""
    gamma = _fractional_year(date_local, 12)
    offset = _equation_of_time_minutes(gamma) + 4 * longitude_deg - 60 * UTC_OFFSET_HOURS
    latitude = math.radians(latitude_deg)
    declination = _solar_declination_rad(gamma)
    hour_angle = math.degrees(math.acos(
        math.cos(math.radians(_ZENITH_DEGREES)) / (math.cos(latitude) * math.cos(declination))
        - math.tan(latitude) * math.tan(declination)))
    noon_minutes = 720 - offset
    midnight = datetime(date_local.year, date_local.month, date_local.day, tzinfo=LOCAL_TZ)
    return (midnight + timedelta(minutes=noon_minutes - 4 * hour_angle),
            midnight + timedelta(minutes=noon_minutes + 4 * hour_angle))
