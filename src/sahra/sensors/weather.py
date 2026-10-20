import json
from datetime import datetime
from pathlib import Path

from ..risk import wbgt_outdoor_c
from ..solar import LOCAL_TZ, cos_zenith
from ..types import WeatherReading

_SITE_LATITUDE_DEG = 25.2048
_SITE_LONGITUDE_DEG = 55.2708


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


class HourlyWeatherProvider:
    """Time-indexed weather from a committed hourly fixture: one archived day,
    one hour per reading. The outdoor WBGT is derived from the fixture's own
    irradiance and wind, so the index carries the exposure peak of the day
    rather than a single midday row.

    The fixture is the zone, so `zone_id` is accepted for interface parity
    with `WeatherProvider` and does not select data. An `at` outside the
    archived hours raises KeyError.
    """

    def __init__(self, fixture_path: Path | str):
        payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        self._rows = {datetime.fromisoformat(row["time"]): row for row in payload["hours"]}

    def sample(self, zone_id: str, at: datetime) -> WeatherReading:
        row = self._rows[self._local_key(at)]
        solar = row["global_radiation_wm2"]
        direct_fraction = row["direct_radiation_wm2"] / solar if solar > 0 else 0.8
        index = wbgt_outdoor_c(
            row["air_temp_c"], row["humidity_pct"], solar, row["wind_ms"],
            cos_zenith(_SITE_LATITUDE_DEG, _SITE_LONGITUDE_DEG, at),
            direct_fraction,
        )
        return WeatherReading(
            air_temp_c=row["air_temp_c"],
            humidity_pct=row["humidity_pct"],
            wbgt_c=index,
            solar_wm2=solar,
        )

    def hours(self, zone_id: str) -> list[datetime]:
        return sorted(self._rows)

    @staticmethod
    def _local_key(at: datetime) -> datetime:
        if at.tzinfo is None:
            return at.replace(tzinfo=LOCAL_TZ)
        return at.astimezone(LOCAL_TZ)
