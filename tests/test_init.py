"""Integration tests for __init__.py: full setup/unload against a mocked API.

Supersedes the Gate 3 step 1 placeholder, which only tested inert stub
functions - now that OAuth, the coordinator, and sensors are all real,
these test the actual setup path (T14: unload/reload with no orphaned
listeners).
"""

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.concept2_logbook.const import (
    API_BASE_URL,
    CONF_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from custom_components.concept2_logbook.sensor import SENSOR_DESCRIPTIONS

CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"


def _mock_results_and_challenges(
    aioclient_mock, *, results=None, current_challenge=None
):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": results or [],
            "meta": {"pagination": {"total_pages": 1, "current_page": 1}},
        },
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/challenges/current",
        json={"data": [current_challenge] if current_challenge else []},
    )
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/upcoming/30", json={"data": []})


async def _setup_entry(
    hass, aioclient_mock, *, results=None, current_challenge=None
) -> MockConfigEntry:
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET), "test"
    )
    _mock_results_and_challenges(
        aioclient_mock, results=results, current_challenge=current_challenge
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={
            "auth_implementation": "test",
            "token": {
                "access_token": "mock-access-token",
                "refresh_token": "mock-refresh-token",
                "expires_in": 604800,
                "expires_at": 9999999999,
            },
            "full_history_sync": False,
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_setup_and_unload_entry_with_empty_history(hass, aioclient_mock):
    """T05-adjacent: first sync with zero results (new/near-empty account)."""
    entry = await _setup_entry(hass, aioclient_mock, results=[])

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state.value == "loaded"

    sensor = hass.states.get("sensor.concept2_logbook_meters_lifetime")
    assert sensor is not None
    assert sensor.state == "0"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state.value == "not_loaded"


async def test_setup_entry_with_one_result(hass, aioclient_mock):
    """Sensors populate from a real (mocked) result."""
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
                "comments": None,
                "calories_total": 250,
                "stroke_rate": 24,
                "stroke_count": 200,
                "drag_factor": 120,
                "heart_rate": {"average": 150, "min": 120, "max": 170, "ending": 155},
            }
        ],
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    distance = hass.states.get("sensor.concept2_logbook_last_workout_distance")
    assert distance.state == "5000"
    assert distance.attributes["machine_type"] == "rower"

    time_sensor = hass.states.get("sensor.concept2_logbook_last_workout_time")
    assert time_sensor.state == "1200.0"  # 12000 tenths of a second -> seconds

    done_today = hass.states.get("binary_sensor.concept2_logbook_workout_done_today")
    assert done_today.state == "on"


async def test_every_declared_sensor_is_actually_created(hass, aioclient_mock):
    """Catches wiring gaps a coordinator-only test can't see (e.g. a bad
    translation_key silently producing no entity) - every sensor description
    plus the binary sensor should show up in the entity registry.
    """
    entry = await _setup_entry(hass, aioclient_mock, results=[])
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    unique_ids = {e.unique_id for e in entries}

    expected = {
        f"{entry.entry_id}_{description.key}" for description in SENSOR_DESCRIPTIONS
    }
    expected.add(f"{entry.entry_id}_workout_done_today")

    assert expected == unique_ids


async def test_current_challenge_sensor_exposes_attributes(hass, aioclient_mock):
    """The challenge sensor's extra_state_attributes had never been read at
    the entity level - only checked at the coordinator data level.
    """
    entry = await _setup_entry(
        hass,
        aioclient_mock,
        results=[],
        current_challenge={
            "name": "July Distance Challenge",
            "end_date": "2026-07-31",
            "description": "Row as far as you can in July.",
        },
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.concept2_logbook_current_challenge")
    assert sensor.state == "July Distance Challenge"
    assert sensor.attributes["end_date"] == "2026-07-31"
    assert sensor.attributes["description"] == "Row as far as you can in July."


async def test_changing_options_reloads_with_new_interval(hass, aioclient_mock):
    """F6: changing the polling interval option reloads the entry to pick it up."""
    entry = await _setup_entry(hass, aioclient_mock, results=[])
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 15 * 60

    hass.config_entries.async_update_entry(
        entry, options={CONF_SCAN_INTERVAL_MINUTES: 45}
    )
    await hass.async_block_till_done()

    assert entry.state.value == "loaded"
    assert entry.runtime_data.update_interval.total_seconds() == 45 * 60
