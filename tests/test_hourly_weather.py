import json
from datetime import datetime
from pathlib import Path

import pytest

from sahra.risk import approx_wbgt_c
from sahra.sensors.weather import HourlyWeatherProvider

FIXTURE = Path(__file__).resolve().parents[1] / "data" / "dubai_hourly_2026-07-01.json"


def test_fixture_carries_provenance_and_a_full_day():
    meta = json.loads(FIXTURE.read_text(encoding="utf-8"))["meta"]
    assert "archive-api.open-meteo.com" in meta["source_url"]
    assert meta["retrieved_at"] and meta["license"] and meta["note"]
    assert "reanalysis" in meta["note"].lower()


def test_fixture_has_24_contiguous_hours():
    hours = json.loads(FIXTURE.read_text(encoding="utf-8"))["hours"]
    assert len(hours) == 24
    assert hours[0]["time"].startswith("2026-07-01T00:00")
    assert hours[-1]["time"].startswith("2026-07-01T23:00")


def test_radiation_is_absent_at_night_and_strong_at_midday():
    hours = {h["time"][11:13]: h for h in json.loads(FIXTURE.read_text(encoding="utf-8"))["hours"]}
    assert hours["03"]["global_radiation_wm2"] == 0
    assert hours["12"]["global_radiation_wm2"] > 700


def test_provider_samples_the_hour_and_derives_outdoor_wbgt():
    provider = HourlyWeatherProvider(FIXTURE)
    reading = provider.sample("dubai-2026-07-01", datetime.fromisoformat("2026-07-01T12:00:00+04:00"))
    assert reading.air_temp_c == pytest.approx(36.8, abs=0.2)
    assert reading.wbgt_c is not None
    assert reading.wbgt_c >= approx_wbgt_c(reading.air_temp_c, reading.humidity_pct)


def test_provider_lists_hours_in_order_and_rejects_an_unknown_hour():
    provider = HourlyWeatherProvider(FIXTURE)
    hours = provider.hours("dubai-2026-07-01")
    assert len(hours) == 24 and hours == sorted(hours)
    with pytest.raises(KeyError):
        provider.sample("dubai-2026-07-01", datetime.fromisoformat("2026-07-01T05:30:00+04:00"))
