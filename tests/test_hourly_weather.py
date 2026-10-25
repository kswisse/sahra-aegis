import json
from datetime import datetime, timedelta
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
    assert (meta["latitude"], meta["longitude"]) == (25.202108, 55.302376)
    assert meta["timezone"] == "Asia/Dubai"
    assert meta["zone_id"] == "dubai-2026-07-01"


def test_fixture_has_24_contiguous_hours():
    hours = json.loads(FIXTURE.read_text(encoding="utf-8"))["hours"]
    assert len(hours) == 24
    assert hours[0]["time"].startswith("2026-07-01T00:00")
    assert hours[-1]["time"].startswith("2026-07-01T23:00")
    stamps = [datetime.fromisoformat(h["time"]) for h in hours]
    assert stamps == sorted(stamps)
    assert len(set(stamps)) == 24
    for earlier, later in zip(stamps, stamps[1:]):
        assert later - earlier == timedelta(hours=1)


def test_radiation_is_absent_at_night_and_strong_at_midday():
    hours = {h["time"][11:13]: h for h in json.loads(FIXTURE.read_text(encoding="utf-8"))["hours"]}
    assert hours["03"]["global_radiation_wm2"] == 0
    assert hours["12"]["global_radiation_wm2"] > 700


def test_provider_samples_the_hour_and_derives_outdoor_wbgt():
    provider = HourlyWeatherProvider(FIXTURE)
    reading = provider.sample("dubai-2026-07-01", datetime.fromisoformat("2026-07-01T12:00:00+04:00"))
    assert reading.air_temp_c == pytest.approx(36.8, abs=0.2)
    assert reading.wbgt_c is not None
    assert reading.wbgt_c == pytest.approx(31.335, abs=0.05)
    assert reading.wbgt_c >= approx_wbgt_c(reading.air_temp_c, reading.humidity_pct)


def test_the_provider_names_the_fixture_and_the_hour_when_a_hour_is_missing(tmp_path):
    """A hole in the archive must not read as an ordinary KeyError: the message
    carries the fixture path and the hour, so a corrupt file is diagnosable."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    holed = tmp_path / "holed.json"
    holed.write_text(json.dumps({
        "meta": payload["meta"],
        "hours": [h for h in payload["hours"] if not h["time"].startswith("2026-07-01T12:00")],
    }), encoding="utf-8")

    provider = HourlyWeatherProvider(holed)
    with pytest.raises(KeyError) as missing:
        provider.sample("dubai-2026-07-01", datetime.fromisoformat("2026-07-01T12:00:00+04:00"))

    message = missing.value.args[0]
    assert str(holed) in message
    assert "2026-07-01T12:00:00+04:00" in message


def test_provider_lists_hours_in_order_and_rejects_an_unknown_zone_or_hour():
    provider = HourlyWeatherProvider(FIXTURE)
    hours = provider.hours("dubai-2026-07-01")
    assert len(hours) == 24 and hours == sorted(hours)
    with pytest.raises(KeyError):
        provider.sample("dubai-2026-07-01", datetime.fromisoformat("2026-07-01T05:30:00+04:00"))
    with pytest.raises(KeyError):
        provider.sample("dubai-2026-07-02", datetime.fromisoformat("2026-07-01T12:00:00+04:00"))
    with pytest.raises(KeyError):
        provider.hours("dubai-2026-07-02")
