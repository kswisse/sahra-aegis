"""Replay real archived Dubai weather through the risk engine.

Fixtures were fetched once from the Open-Meteo historical archive (ERA5-backed)
and committed, so validation is offline and reproducible.
ponytail: the live archive fetch is not wired; re-fetch only when the fixture
rows age out, replacing the committed file behind load_fixtures.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .risk import approx_wbgt_c, assess, wbgt_outdoor_c
from .types import HeatState, PopulationGroup, RiskLevel

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "dubai_replay.json"

# RiskLevel is a str enum, so `<` / `>=` fall through to str ordering, which is
# alphabetical and has nothing to do with severity. Rank through this tuple.
_BAND_ORDER = (RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.EXTREME)


def _require(condition: object, msg: str) -> None:
    """Explicit raise so the check survives `python -O` (asserts are stripped)."""
    if not condition:
        raise AssertionError(msg)


@dataclass(frozen=True)
class ReplayDay:
    id: str
    place: str
    date: str
    air_temp_c: float
    humidity_pct: float
    solar_wm2: float
    wind_ms: float
    cos_zenith: float
    direct_fraction: float
    record_air_temp_c: float | None = None

    def outdoor_wbgt_c(self) -> float:
        return wbgt_outdoor_c(self.air_temp_c, self.humidity_pct, self.solar_wm2,
                              self.wind_ms, self.cos_zenith, self.direct_fraction)

    def fallback_wbgt_c(self) -> float:
        return approx_wbgt_c(self.air_temp_c, self.humidity_pct)

    def at(self) -> datetime:
        return datetime.fromisoformat(f"{self.date}T13:00:00+04:00")


def load_fixtures(path: Path | str = FIXTURE) -> list[ReplayDay]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))["days"]
    return [ReplayDay(**row) for row in rows]


def band(day: ReplayDay) -> RiskLevel:
    """Band the day through the real engine, for an outdoor worker."""
    state = HeatState(zone_id=day.id, at=day.at(), air_temp_c=day.air_temp_c,
                      humidity_pct=day.humidity_pct, wbgt_c=day.outdoor_wbgt_c(),
                      source_tier="weather-outdoor")
    return assess(state, PopulationGroup.OUTDOOR_WORKER).level


def severity(level: RiskLevel) -> int:
    """Position of a band in severity order (LOW=0 .. EXTREME=3)."""
    return _BAND_ORDER.index(level)


def render_table(days: Sequence[ReplayDay]) -> str:
    lines = [f"{'day':<34}{'Ta':>6}{'outdoor':>9}{'fallback':>10}{'gap':>6}  band"]
    for d in days:
        out, fb = d.outdoor_wbgt_c(), d.fallback_wbgt_c()
        lines.append(f"{d.id:<34}{d.air_temp_c:6.1f}{out:9.2f}{fb:10.2f}{out - fb:6.2f}  {band(d).value}")
    return "\n".join(lines)


def validate(days: Sequence[ReplayDay]) -> list[str]:
    """Assert the engine against labels it did not produce, and return the
    claims each assertion just checked."""
    claims: list[str] = []

    mohre = [d for d in days if "mohre" in d.id]
    _require(mohre, "no MOHRE-window sample in the fixture")
    for d in mohre:
        _require(band(d) in (RiskLevel.HIGH, RiskLevel.EXTREME), d.id)
    claims.append(f"{len(mohre)} midday sample inside the MOHRE ban window bands HIGH or worse")

    controls = [d for d in days if "control" in d.id]
    _require(controls, "no off-season control in the fixture")
    for d in controls:
        _require(band(d) == RiskLevel.LOW, d.id)
    claims.append(f"{len(controls)} mild off-season control bands LOW")

    for d in days:
        _require(d.outdoor_wbgt_c() > d.fallback_wbgt_c(), d.id)
    claims.append("the solar-aware form exceeds the no-solar fallback on every day")

    sweihan = next(d for d in days if d.id.startswith("ncm-2025-05-24"))
    humid = next(d for d in days if d.id.startswith("dubai-2026-08-05"))
    _require(sweihan.air_temp_c > humid.air_temp_c, "reanalysis order inverted")
    _require(sweihan.outdoor_wbgt_c() < humid.outdoor_wbgt_c(),
             "a hotter but drier day does not band lower")
    _require(severity(band(sweihan)) < severity(band(humid)),
             "a hotter but drier day does not band lower")
    claims.append("a hotter but drier day bands lower than a cooler but more humid one")

    records = [d for d in days if d.record_air_temp_c is not None]
    for d in records:
        _require(d.air_temp_c < d.record_air_temp_c, d.id)
    claims.append(f"{len(records)} reanalysis grid samples sit below their station records")

    return claims


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m sahra.replay",
        description="Replay committed Dubai weather through the risk engine.")
    parser.add_argument("--validate", action="store_true",
                        help="validate only; exit non-zero if a claim fails")
    args = parser.parse_args(argv)

    replayed = load_fixtures()
    if not args.validate:
        print(render_table(replayed))
        for claim in validate(replayed):
            print(f"OK  {claim}")
        return 0

    try:
        claims = validate(replayed)
    except AssertionError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    for claim in claims:
        print(f"OK  {claim}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
