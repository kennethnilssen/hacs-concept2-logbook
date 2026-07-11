"""Tests for diagnostics redaction (T12, C4/OWASP A09)."""

from custom_components.concept2_logbook.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.test_init import _setup_entry


async def test_diagnostics_redacts_tokens_and_identifiers(hass, aioclient_mock):
    entry = await _setup_entry(
        hass,
        aioclient_mock,
        results=[
            {
                "id": 3,
                "date": "2026-07-05 08:00:00",
                "distance": 5000,
                "type": "rower",
                "time": 12000,
                "workout_type": "unknown",
                "source": "Web",
                "verified": False,
                "ranked": False,
                "comments": "Felt great today, personal best!",
                "calories_total": 250,
            }
        ],
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"]["access_token"] == "**REDACTED**"
    assert diagnostics["entry"]["unique_id"] == "**REDACTED**"
    assert diagnostics["data"]["last_result"]["comments"] == "**REDACTED**"

    # Everything else useful for support should still be present.
    assert diagnostics["data"]["last_result"]["distance"] == 5000
    assert diagnostics["data"]["totals"]["meters_lifetime"] == 5000
    assert diagnostics["coordinator"]["result_count"] == 1
    assert diagnostics["coordinator"]["last_synced_at"] is not None
