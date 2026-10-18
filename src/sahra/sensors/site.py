from ..types import SiteReading


class SiteProvider:
    """On-site WBGT sensor at the schoolyard or work site. Absence is normal:
    zones without a sensor fall back to the weather tier."""

    def __init__(self, fixtures: dict[str, dict]):
        self._fixtures = fixtures

    def sample(self, zone_id: str) -> SiteReading | None:
        row = self._fixtures.get(zone_id)
        return SiteReading(wbgt_c=row["wbgt_c"]) if row else None
