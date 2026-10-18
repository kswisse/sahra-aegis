from ..types import SatelliteReading


class SatelliteProvider:
    """Satellite land-surface temperature (regional, ~1 km). This is the only
    module allowed to import geospatial libraries when live. Offline it serves
    fixtures, and returns None rather than guessing."""

    def __init__(self, fixtures: dict[str, float], online: bool = False):
        self._fixtures = fixtures
        self._online = online

    def lst_for(self, zone_id: str) -> SatelliteReading | None:
        if self._online:
            pass  # ponytail: live STAC query lands here; fixtures cover the demo
        value = self._fixtures.get(zone_id)
        return SatelliteReading(lst_c=value) if value is not None else None
