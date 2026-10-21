# tests/test_extreme_day.py
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sahra.fusion import fuse
from sahra.risk import assess
from sahra.sensors.weather import HourlyWeatherProvider
from sahra.types import PopulationGroup, RiskLevel

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "dubai_hourly_2026-08-13.json"
ZONE = "dubai-2026-08-13"


def test_fixture_provenance_is_complete_and_labels_the_day_as_reanalysis():
    meta = json.loads(FIXTURE.read_text(encoding="utf-8"))["meta"]
    assert "archive-api.open-meteo.com" in meta["source_url"]
    assert "start_date=2026-08-13" in meta["source_url"]
    assert meta["source"] and meta["dataset"]
    assert meta["retrieved_at"] and meta["license"] and meta["note"]
    assert meta["sunrise"] and meta["sunset"]
    assert (meta["latitude"], meta["longitude"]) == (25.202108, 55.302376)
    assert meta["elevation_m"] == 6
    assert meta["timezone"] == "Asia/Dubai"
    assert meta["zone_id"] == ZONE
    note = meta["note"].lower()
    assert "reanalysis" in note
    assert "45.9" in note
    assert "not" in note and "anchor" in note


def test_fixture_has_24_contiguous_hours_and_a_45_9_daily_maximum():
    hours = json.loads(FIXTURE.read_text(encoding="utf-8"))["hours"]
    assert len(hours) == 24
    assert hours[0]["time"].startswith("2026-08-13T00:00")
    assert hours[-1]["time"].startswith("2026-08-13T23:00")
    stamps = [datetime.fromisoformat(h["time"]) for h in hours]
    assert stamps == sorted(stamps)
    assert len(set(stamps)) == 24
    for earlier, later in zip(stamps, stamps[1:]):
        assert later - earlier == timedelta(hours=1)
    assert max(h["air_temp_c"] for h in hours) == pytest.approx(45.9, abs=0.05)


def test_the_derived_outdoor_wbgt_reaches_the_extreme_band():
    provider = HourlyWeatherProvider(FIXTURE)
    banded = []
    for at in provider.hours(ZONE):
        reading = provider.sample(ZONE, at)
        state = fuse(ZONE, at, None, reading, None)
        banded.append((at, reading, assess(state, PopulationGroup.OUTDOOR_WORKER)))

    extreme = [at for at, _, a in banded if a.level is RiskLevel.EXTREME]
    assert extreme, "the archived extreme day must band extreme at some hour"

    peak_at, peak_reading, peak = max(banded, key=lambda row: row[1].wbgt_c)
    assert peak_reading.wbgt_c >= 32.0
    assert peak.level is RiskLevel.EXTREME
    assert peak_reading.wbgt_c == pytest.approx(34.47, abs=0.05)
    assert peak_at == datetime.fromisoformat("2026-08-13T14:00:00+04:00")
