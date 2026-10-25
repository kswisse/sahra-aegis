import json
from datetime import datetime
from pathlib import Path

from ..risk import wbgt_outdoor_c
from ..solar import LOCAL_TZ, cos_zenith
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


class HourlyWeatherProvider:
    """Time-indexed weather from a committed hourly fixture: one archived day,
    one hour per reading. The site identity (coordinates, zone) comes from the
    fixture's own metadata, so the provider holds no site constants. The
    outdoor WBGT is derived from the fixture's irradiance and wind, so the
    index carries the exposure peak of the day rather than a single midday row.

    `zone_id` must name the fixture's zone; an unknown zone, or an hour
    outside the archive, raises KeyError.
    """

    def __init__(self, fixture_path: Path | str):
        self._path = Path(fixture_path)
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        meta = payload["meta"]
        self._zone_id = meta["zone_id"]
        self._latitude_deg = meta["latitude"]
        self._longitude_deg = meta["longitude"]
        self._rows = {datetime.fromisoformat(row["time"]): row for row in payload["hours"]}

    def sample(self, zone_id: str, at: datetime) -> WeatherReading:
        self._check_zone(zone_id)
        key = self._local_key(at)
        row = self._rows.get(key)
        if row is None:
            raise KeyError(f"{self._path}: no row for {key.isoformat()}")
        solar = row["global_radiation_wm2"]
        direct_fraction = row["direct_radiation_wm2"] / solar if solar > 0 else 0.8
        index = wbgt_outdoor_c(
            row["air_temp_c"], row["humidity_pct"], solar, row["wind_ms"],
            cos_zenith(self._latitude_deg, self._longitude_deg, at),
            direct_fraction,
        )
        return WeatherReading(
            air_temp_c=row["air_temp_c"],
            humidity_pct=row["humidity_pct"],
            wbgt_c=index,
            solar_wm2=solar,
        )

    def hours(self, zone_id: str) -> list[datetime]:
        self._check_zone(zone_id)
        return sorted(self._rows)

    def _check_zone(self, zone_id: str) -> None:
        if zone_id != self._zone_id:
            raise KeyError(zone_id)

    @staticmethod
    def _local_key(at: datetime) -> datetime:
        if at.tzinfo is None:
            return at.replace(tzinfo=LOCAL_TZ)
        return at.astimezone(LOCAL_TZ)
