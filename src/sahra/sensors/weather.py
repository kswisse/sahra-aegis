from datetime import datetime

from ..risk import wbgt_outdoor_c
from ..types import WeatherReading


class WeatherProvider:
    """Gridded weather. Reads from a fixture mapping; a live HTTP client
    replaces the mapping behind this same interface. A row that also carries
    solar, wind and zenith yields the outdoor WBGT index, which is the value
    the risk engine prefers when no site sensor exists."""

    _NEEDED = ("solar_wm2", "wind_ms", "cos_zenith")

    def __init__(self, fixtures: dict[str, dict]):
        self._fixtures = fixtures

    def sample(self, zone_id: str, at: datetime) -> WeatherReading:
        row = self._fixtures[zone_id]
        index = None
        if all(key in row for key in self._NEEDED):
            index = wbgt_outdoor_c(
                row["air_temp_c"], row["humidity_pct"],
                row["solar_wm2"], row["wind_ms"], row["cos_zenith"],
            )
        return WeatherReading(
            air_temp_c=row["air_temp_c"],
            humidity_pct=row["humidity_pct"],
            wbgt_c=index,
            solar_wm2=row.get("solar_wm2"),
        )
