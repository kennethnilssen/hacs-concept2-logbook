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
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    EVENT_NEW_RESULT,
)
from custom_components.concept2_logbook.coordinator import Concept2Coordinator


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


def _make_coordinator(
    hass, entry_data: dict | None = None, entry: MockConfigEntry | None = None
) -> Concept2Coordinator:
    if entry is None:
        entry = MockConfigEntry(domain=DOMAIN, data=entry_data or {})
        entry.add_to_hass(hass)
    client = Concept2ApiClient(
        session=async_get_clientsession(hass), token="test-token"
    )
    return Concept2Coordinator(hass, entry, client)


async def test_coordinator_uses_default_interval_with_no_options(hass):
    coordinator = _make_coordinator(hass)
    assert coordinator.update_interval == timedelta(
        minutes=DEFAULT_SCAN_INTERVAL_MINUTES
    )


async def test_coordinator_uses_configured_interval_from_options(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, options={CONF_SCAN_INTERVAL_MINUTES: 45}
    )
    entry.add_to_hass(hass)
    coordinator = _make_coordinator(hass, entry=entry)
    assert coordinator.update_interval == timedelta(minutes=45)


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
    assert data.last_synced_at == coordinator._last_synced_at
    assert data.last_synced_at is not None


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


async def test_reload_does_not_suppress_event_for_new_result(hass, aioclient_mock):
    """Regression: a coordinator reload (new in-memory instance, same entry/
    store - e.g. an HA restart or the user reloading the integration) must not
    treat a subsequent genuinely-new result as part of "the initial sync".
    Only a true first-ever sync (no persisted last_synced_at) should suppress
    events - that state must survive reconstruction, not live on an in-memory
    flag that resets every time the coordinator object is recreated.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [_result(1, date="2026-07-05 08:00:00")],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass, entry=entry)
    await coordinator.async_setup()
    await coordinator._async_update_data()  # true first sync - persists state

    # Simulate a reload: a brand-new coordinator instance for the same entry.
    reloaded = _make_coordinator(hass, entry=entry)
    await reloaded.async_setup()

    events = []
    hass.bus.async_listen(EVENT_NEW_RESULT, lambda event: events.append(event))

    since = reloaded._last_synced_at
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

    await reloaded._async_update_data()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["result"]["id"] == 2


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


async def test_store_round_trip_survives_a_restart(hass, aioclient_mock):
    """§4.1.1's whole point: state must actually survive a coordinator reload.

    Every other test builds one coordinator and keeps calling it - none of
    them prove the Store save/load round-trip itself works. This is the one
    test that does: build coordinator A, sync it, then build a *second*,
    independent coordinator B against the same config entry (simulating a
    HA restart) and confirm it restores the same state from disk rather
    than starting cold.
    """
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [_result(1, date="2026-07-01 08:00:00", distance=5000)],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    coordinator_a = _make_coordinator(hass, entry=entry)
    await coordinator_a.async_setup()
    await coordinator_a._async_update_data()

    assert coordinator_a._last_synced_at is not None
    assert coordinator_a._last_full_sync_at is not None

    # A brand-new coordinator instance, same entry_id -> same Store file.
    coordinator_b = _make_coordinator(hass, entry=entry)
    assert coordinator_b._results == {}  # cold before async_setup, as expected

    await coordinator_b.async_setup()

    assert coordinator_b._results == coordinator_a._results
    assert coordinator_b._last_synced_at == coordinator_a._last_synced_at
    assert coordinator_b._last_full_sync_at == coordinator_a._last_full_sync_at


async def test_workout_streak_counts_consecutive_days_and_stops_at_gap(
    hass, aioclient_mock, freezer
):
    """Streak logic has never been asserted directly - do it explicitly.

    Freezes time - the fixture dates below only mean "2 days ago/yesterday/
    today" relative to a pinned "now", not whatever day the suite runs on.
    """
    freezer.move_to("2026-07-05 12:00:00")
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [
                _result(1, date="2026-07-03 08:00:00"),  # 2 days ago
                _result(2, date="2026-07-04 08:00:00"),  # yesterday
                _result(3, date="2026-07-05 08:00:00"),  # today
                _result(4, date="2026-06-20 08:00:00"),  # older, breaks the streak
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert data.totals["workout_streak"] == 3
    assert data.totals["workout_done_today"] is True


async def test_challenge_sensors_populate_from_real_data(hass, aioclient_mock):
    """Every other test mocks challenges as empty - verify the non-empty path too."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={"data": [], "meta": {"pagination": {"total_pages": 1}}},
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/challenges/current",
        json={
            "data": [
                {
                    "name": "July Distance Challenge",
                    "end_date": "2026-07-31",
                    "description": "Row as far as you can in July.",
                }
            ]
        },
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/challenges/upcoming/30",
        json={
            "data": [
                {
                    "name": "August Sprint",
                    "end_date": "2026-08-31",
                    "description": "Sprint challenge starting in August.",
                }
            ]
        },
    )
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert data.current_challenge["name"] == "July Distance Challenge"
    assert data.upcoming_challenge["name"] == "August Sprint"


async def test_generic_api_error_raises_update_failed_not_a_crash(hass, aioclient_mock):
    """A plain 403 (not 401/429/5xx) must still surface as UpdateFailed."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me/results", status=403)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_retry_after_non_numeric_header_falls_back_to_exponential_backoff(
    hass, aioclient_mock
):
    """Retry-After can legally be an HTTP-date, not just seconds - must not crash."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        status=429,
        headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
    )
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._backoff_until is not None


async def test_season_boundary_uses_previous_year_before_may(
    hass, aioclient_mock, freezer
):
    """Concept2 season is May 1 - Apr 30 (CLAUDE.md); the pre-May branch of
    _season_start had never actually run - every other test's "today" was in
    July. Freeze "today" to March and confirm the season boundary lands in
    the *previous* calendar year, and a result from last year's May counts,
    while one from two seasons ago doesn't.
    """
    freezer.move_to("2026-03-15 12:00:00")
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [
                _result(1, date="2025-06-01 08:00:00", distance=4000),  # this season
                _result(2, date="2024-06-01 08:00:00", distance=9000),  # last season
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert data.totals["meters_this_season"] == 4000
    assert data.totals["meters_lifetime"] == 13000


async def test_streak_is_zero_with_no_recent_workouts(hass, aioclient_mock, freezer):
    """Streak edge case: nothing in the last two days -> streak is 0, not stale."""
    freezer.move_to("2026-07-05 12:00:00")
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [_result(1, date="2026-06-01 08:00:00")],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert data.totals["workout_streak"] == 0
    assert data.totals["workout_done_today"] is False


async def test_streak_continues_from_yesterday_if_none_logged_today_yet(
    hass, aioclient_mock, freezer
):
    """Haven't rowed yet today - streak should still count from yesterday back."""
    freezer.move_to("2026-07-05 12:00:00")
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [
                _result(1, date="2026-07-03 08:00:00"),  # 2 days ago
                _result(2, date="2026-07-04 08:00:00"),  # yesterday
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert data.totals["workout_streak"] == 2
    assert data.totals["workout_done_today"] is False


async def test_non_dict_and_bad_date_results_are_both_skipped(hass, aioclient_mock):
    """_is_valid_result's other defensive branches: a non-dict item in the
    results array, a dict with an unparseable date string, and a dict where
    "date" isn't a string at all.
    """
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={
            "data": [
                "not-a-dict",
                {"id": 2, "date": "not-a-date", "distance": 1000},
                {"id": 4, "date": 20260705, "distance": 1000},
                _result(3, date="2026-07-05 08:00:00"),
            ],
            "meta": {"pagination": {"total_pages": 1}},
        },
    )
    _mock_challenges(aioclient_mock)
    coordinator = _make_coordinator(hass)
    await coordinator.async_setup()

    data = await coordinator._async_update_data()

    assert set(coordinator._results) == {"3"}
    assert data.totals["meters_lifetime"] == 5000


async def test_due_for_reconciliation_treats_missing_timestamp_as_overdue(hass):
    """Migration fallback: old stored data without last_full_sync_at at all
    (predating this field) should be treated as overdue, not crash.
    """
    coordinator = _make_coordinator(hass)
    coordinator._results = {"1": _result(1, date="2026-07-01 08:00:00")}
    assert coordinator._last_full_sync_at is None

    assert coordinator._due_for_reconciliation() is True
