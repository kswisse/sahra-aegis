from datetime import datetime

from .types import HeatState, SatelliteReading, SiteReading, WeatherReading

TIER_DISAGREEMENT_C = 1.0
LST_AIR_GAP_C = 15.0


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
    sole basis for a zone-level decision, so it only populates lst_c.

    When a site sensor and the weather tier both yield an index and they differ
    by more than TIER_DISAGREEMENT_C, the higher reading wins: an unresolved
    disagreement is resolved conservatively, and the note says which two values
    met and which one was taken. A disagreement of at most 1 C keeps the site
    sensor, as before."""
    notes: list[str] = []
    wbgt_c = site.wbgt_c if site else weather.wbgt_c
    tier = _tier(site, weather)
    if site is not None and weather.wbgt_c is not None:
        weather_tier = _tier(None, weather)
        gap = abs(site.wbgt_c - weather.wbgt_c)
        if gap > TIER_DISAGREEMENT_C:
            if site.wbgt_c > weather.wbgt_c:
                wbgt_c, tier = site.wbgt_c, "site"
            else:
                wbgt_c, tier = weather.wbgt_c, weather_tier
            notes.append(
                f"tiers disagree: site {site.wbgt_c:.1f} C vs {weather_tier} "
                f"{weather.wbgt_c:.1f} C, gap {gap:.1f} C; chose the higher, "
                f"conservative {wbgt_c:.1f} C from {tier}")
    if satellite is not None:
        gap = satellite.lst_c - weather.air_temp_c
        if gap > LST_AIR_GAP_C:
            notes.append(
                f"satellite LST {satellite.lst_c:.1f} C is {gap:.1f} C above air "
                f"{weather.air_temp_c:.1f} C: advisory only, never the sole basis")
    return HeatState(
        zone_id=zone_id,
        at=at,
        air_temp_c=weather.air_temp_c,
        humidity_pct=weather.humidity_pct,
        wbgt_c=wbgt_c,
        lst_c=satellite.lst_c if satellite else None,
        source_tier=tier,
        disagreement="; ".join(notes) or None,
    )
