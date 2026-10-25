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
    """Merge tiered readings by precedence.

    Site wins; the weather tier supplies the index when no site sensor reports.
    A site-vs-weather conflict is **not** resolved here: the observation carries
    both indices and PredictAgent raises it to the arbiter, which owns the
    ruling. Satellite LST is regional and can never be the sole basis for a
    zone-level decision, so it only populates lst_c and an advisory note.
    """
    notes: list[str] = []
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
        wbgt_c=site.wbgt_c if site else weather.wbgt_c,
        lst_c=satellite.lst_c if satellite else None,
        source_tier=_tier(site, weather),
        disagreement="; ".join(notes) or None,
    )
