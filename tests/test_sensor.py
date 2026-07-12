"""Tests for sensor.py entity value functions."""

from datetime import datetime

from homeassistant.util import dt as dt_util

from custom_components.concept2_logbook.coordinator import Concept2Data
from custom_components.concept2_logbook.sensor import _last_synced_at


def test_last_synced_at_returns_none_when_not_set():
    assert _last_synced_at(Concept2Data()) is None


def test_last_synced_at_parses_as_utc():
    """Unlike workout dates, our own sync timestamp is generated with
    dt_util.utcnow() - it's already known-UTC, no local-timezone guess.
    """
    data = Concept2Data(last_synced_at="2026-07-12 10:19:47")

    result = _last_synced_at(data)

    assert result == datetime(2026, 7, 12, 10, 19, 47, tzinfo=dt_util.UTC)
