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
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.concept2_logbook.const import API_BASE_URL, DOMAIN

CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"


def _mock_results_and_challenges(aioclient_mock, *, results=None):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": results or [],
            "meta": {"pagination": {"total_pages": 1, "current_page": 1}},
        },
    )
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/current", json={"data": []})
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/upcoming/30", json={"data": []})


async def _setup_entry(hass, aioclient_mock, *, results=None) -> MockConfigEntry:
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET), "test"
    )
    _mock_results_and_challenges(aioclient_mock, results=results)

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
