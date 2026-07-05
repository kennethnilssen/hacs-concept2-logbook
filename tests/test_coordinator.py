"""Tests for Concept2Coordinator (T05-T10, T15)."""

from datetime import timedelta

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.concept2_logbook.api import Concept2ApiClient
from custom_components.concept2_logbook.const import (
    API_BASE_URL,
    DOMAIN,
    EVENT_NEW_RESULT,
)
from custom_components.concept2_logbook.coordinator import Concept2Coordinator


class FakeOAuthSession:
    def __init__(self) -> None:
        self.token = {"access_token": "test-token"}

    async def async_ensure_token_valid(self) -> None:
        return None


def _mock_challenges(aioclient_mock) -> None:
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/current", json={"data": []})
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/upcoming/30", json={"data": []})


def _result(result_id: int, *, date: str, distance: int = 5000) -> dict:
    return {
        "id": result_id,
        "date": date,
        "distance": distance,
        "type": "rower",
        "time": 12000,
        "workout_type": "unknown",
        "source": "Web",
        "verified": False,
        "ranked": False,
        "comments": None,
        "calories_total": 250,
    }


def _make_coordinator(hass, entry_data: dict | None = None) -> Concept2Coordinator:
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data or {})
    entry.add_to_hass(hass)
    client = Concept2ApiClient(
        session=async_get_clientsession(hass),
        oauth_session=FakeOAuthSession(),
    )
    return Concept2Coordinator(hass, entry, client)


async def test_first_sync_populates_data_without_firing_event(hass, aioclient_mock):
    """T05: first sync with N results populates data, fires no event."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [_result(1, date="2026-07-05 08:00:00")],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    events = []
    hass.bus.async_listen(EVENT_NEW_RESULT, lambda event: events.append(event))

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert data.last_result["id"] == 1
    assert data.totals["meters_lifetime"] == 5000
    assert events == []


async def test_incremental_sync_fires_event_for_new_result_only(hass, aioclient_mock):
    """T06: a second poll that finds exactly one new result fires exactly one event."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [_result(1, date="2026-07-05 08:00:00")],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()
    await coordinator._async_update_data()

    events = []
    hass.bus.async_listen(EVENT_NEW_RESULT, lambda event: events.append(event))

    since = coordinator._last_synced_at
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?updated_after={since}",
        json={
            "data": [
                _result(1, date="2026-07-05 08:00:00"),  # unchanged
                _result(2, date="2026-07-05 09:00:00"),  # genuinely new
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["result"]["id"] == 2
    assert data.totals["meters_lifetime"] == 10000


async def test_result_update_reflected_without_firing_event(hass, aioclient_mock):
    """T10: an edited result updates totals on next poll, without firing an event."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [_result(1, date="2026-07-05 08:00:00", distance=5000)],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()
    await coordinator._async_update_data()

    events = []
    hass.bus.async_listen(EVENT_NEW_RESULT, lambda event: events.append(event))

    since = coordinator._last_synced_at
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?updated_after={since}",
        json={
            "data": [_result(1, date="2026-07-05 08:00:00", distance=7500)],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)

    data = await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert data.totals["meters_lifetime"] == 7500
    assert events == []


async def test_pagination_processes_every_result_exactly_once(hass, aioclient_mock):
    """T09: a full sync across multiple pages processes each result once."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?page=1",
        json={
            "data": [_result(1, date="2026-01-01 08:00:00")],
            "meta": {"pagination": {"total_pages": 2}},
        },
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?page=2",
        json={
            "data": [_result(2, date="2026-02-01 08:00:00")],
            "meta": {"pagination": {"total_pages": 2}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass, {"full_history_sync": True})
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert set(coordinator._results) == {"1", "2"}
    assert data.totals["meters_lifetime"] == 10000


async def test_rate_limit_backs_off_and_recovers(hass, aioclient_mock):
    """T07: a 429 triggers backoff; a later successful poll recovers."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={"data": [], "meta": {"pagination": {"total_pages": 1}}},
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()
    await coordinator._async_update_data()

    since = coordinator._last_synced_at
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?updated_after={since}",
        status=429,
        headers={"Retry-After": "120"},
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._backoff_until is not None
    calls_before = len(aioclient_mock.mock_calls)

    # Immediately polling again must not hit the API at all while backing off.
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert len(aioclient_mock.mock_calls) == calls_before

    # Simulate the backoff window passing, then a healthy poll recovers.
    coordinator._backoff_until = dt_util.utcnow() - timedelta(seconds=1)
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?updated_after={since}",
        json={"data": [], "meta": {"pagination": {"total_pages": 1}}},
    )
    _mock_challenges(aioclient_mock)

    data = await coordinator._async_update_data()
    assert coordinator._backoff_until is None
    assert data.totals["meters_lifetime"] == 0


async def test_auth_error_triggers_reauth(hass, aioclient_mock):
    """F5: a 401 raises ConfigEntryAuthFailed so HA starts a reauth flow."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me/results", status=401)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_malformed_result_is_skipped_not_fatal(hass, aioclient_mock):
    """T08: a malformed result is logged and skipped, not a crash."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [
                {"id": 1},  # missing required fields
                _result(2, date="2026-07-05 08:00:00"),
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert set(coordinator._results) == {"2"}
    assert data.totals["meters_lifetime"] == 5000


async def test_deleted_result_removed_on_reconciliation(hass, aioclient_mock):
    """T15: a result deleted upstream is removed from totals on reconciliation."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [
                _result(1, date="2026-01-01 08:00:00", distance=5000),
                _result(2, date="2026-02-01 08:00:00", distance=3000),
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass, {"full_history_sync": True})
    await coordinator.async_setup()
    data = await coordinator._async_update_data()
    assert data.totals["meters_lifetime"] == 8000

    # Force the next poll to treat this as due for reconciliation.
    coordinator._last_full_sync_at = dt_util.utcnow() - timedelta(hours=25)
    aioclient_mock.clear_requests()
    # Result id 2 no longer comes back at all - it was deleted upstream.
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results?from=2026-01-01 08:00:00",
        json={
            "data": [_result(1, date="2026-01-01 08:00:00", distance=5000)],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)

    data = await coordinator._async_update_data()

    assert set(coordinator._results) == {"1"}
    assert data.totals["meters_lifetime"] == 5000
