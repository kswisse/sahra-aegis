from datetime import datetime

from .types import HeatState, SatelliteReading, SiteReading, WeatherReading


def _tier(site: SiteReading | None, weather: WeatherReading) -> str:
    """Which tier supplied the decision-critical value."""
    if site is not None:
        return "site"
    return "weather-outdoor" if weather.wbgt_c is not None else "weather"


def fuse(
    zone_id: str,
    at: datetime,
    satellite: SatelliteReading | None,
    weather: WeatherReading,
    site: SiteReading | None,
) -> HeatState:
    """Merge tiered readings. Satellite LST is regional and can never be the
    sole basis for a zone-level decision, so it only populates lst_c."""
    return HeatState(
        zone_id=zone_id,
        at=at,
        air_temp_c=weather.air_temp_c,
        humidity_pct=weather.humidity_pct,
        wbgt_c=site.wbgt_c if site else weather.wbgt_c,
        lst_c=satellite.lst_c if satellite else None,
        source_tier=_tier(site, weather),
    )
