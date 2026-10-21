import math

from .types import HeatState, PopulationGroup, RiskAssessment, RiskLevel

THRESHOLD_C = 28.0
VULNERABILITY = {PopulationGroup.SCHOOL: 1.0, PopulationGroup.OUTDOOR_WORKER: 1.05}

_SIGMA = 5.67e-8          # Stefan-Boltzmann constant, W m-2 K-4
_H_CONVECTIVE = 0.228    # NWS daytime convective coefficient
_GLOBE_NUM = 7680000.0
_GLOBE_DENOM = 256000.0


def _stull_wet_bulb_c(air_temp_c: float, humidity_pct: float) -> float:
    """Stull (2011) natural wet-bulb from dry-bulb and RH."""
    rh = humidity_pct
    return (
        air_temp_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(air_temp_c + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )


def approx_wbgt_c(air_temp_c: float, humidity_pct: float) -> float:
    """No-solar WBGT fallback, 0.7*Tnw + 0.3*Ta.
    ponytail: no radiation term, so it understates outdoor WBGT in the sun
    (measured shade-vs-sun gap ~3-4 C, up to ~10 C against a full model in
    extreme hot-dry low-wind conditions, Kong & Huber 2022). Prefer
    wbgt_outdoor_c whenever solar irradiance is available."""
    return 0.7 * _stull_wet_bulb_c(air_temp_c, humidity_pct) + 0.3 * air_temp_c


def _saturation_vapour_pressure_hpa(air_temp_c: float) -> float:
    return 6.105 * math.exp(17.27 * air_temp_c / (237.7 + air_temp_c))


def globe_temp_c(
    air_temp_c: float,
    solar_wm2: float,
    wind_ms: float,
    cos_zenith: float,
    direct_fraction: float = 0.8,
) -> float:
    """Black-globe temperature, Dimiceli et al. (2011, 2013), in the form the US
    National Weather Service runs operationally:
    Tg = (B + C*Ta + 7680000) / (C + 256000), with the NWS daytime convective
    coefficient and wind floored at 1 m/s. A negative irradiance is a data
    error, not a cooling effect, so it is clamped to 0."""
    u = max(wind_ms, 1.0)
    solar = max(solar_wm2, 0.0)
    f_dir = min(max(direct_fraction, 0.0), 1.0)
    f_dif = 1.0 - f_dir
    emissivity = 0.575 * _saturation_vapour_pressure_hpa(air_temp_c) ** (1.0 / 7.0)
    b = (
        solar * (f_dir / (4.0 * _SIGMA * max(cos_zenith, 0.05)) + 1.2 * f_dif / _SIGMA)
        + emissivity * air_temp_c ** 4
    )
    c = _H_CONVECTIVE * (u * 3600.0) ** 0.58 / 5.3865e-8
    return (b + c * air_temp_c + _GLOBE_NUM) / (c + _GLOBE_DENOM)


def wbgt_outdoor_c(
    air_temp_c: float,
    humidity_pct: float,
    solar_wm2: float,
    wind_ms: float,
    cos_zenith: float,
    direct_fraction: float = 0.8,
) -> float:
    """ISO 7243 outdoor WBGT, 0.7*Tnw + 0.2*Tg + 0.1*Ta, with the solar-aware
    globe term. Use it whenever solar irradiance is available: solar=0 collapses
    it onto the fallback, and on a hot dry day it is worth ~2-3 C of index and
    can move the band."""
    tg = globe_temp_c(air_temp_c, solar_wm2, wind_ms, cos_zenith, direct_fraction)
    return 0.7 * _stull_wet_bulb_c(air_temp_c, humidity_pct) + 0.2 * tg + 0.1 * air_temp_c


def _level(wbgt_c: float) -> RiskLevel:
    if wbgt_c < THRESHOLD_C:
        return RiskLevel.LOW
    if wbgt_c < 30.0:
        return RiskLevel.MODERATE
    if wbgt_c < 32.0:
        return RiskLevel.HIGH
    return RiskLevel.EXTREME


def assess(state: HeatState, group: PopulationGroup) -> RiskAssessment:
    wbgt = state.wbgt_c
    if wbgt is None:
        wbgt = approx_wbgt_c(state.air_temp_c, state.humidity_pct)
    level = _level(wbgt)
    raw = min(max((wbgt - THRESHOLD_C) / 6.0, 0.0), 1.0)
    score = min(raw * VULNERABILITY[group] + (0.0 if wbgt < THRESHOLD_C else 0.1), 1.0)
    return RiskAssessment(zone_id=state.zone_id, at=state.at, group=group,
                          wbgt_c=round(wbgt, 1), score=round(score, 3), level=level)
