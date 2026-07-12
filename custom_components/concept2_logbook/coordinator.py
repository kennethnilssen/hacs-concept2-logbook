"""DataUpdateCoordinator for Concept2 Logbook.

Polls the Concept2 API (F2), maintains a local result store so aggregate
totals can be recomputed correctly when a historical result is edited or
deleted upstream (design doc §4.1.1), and fires `concept2_new_result` for
genuinely new results once the initial sync has completed (F4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    Concept2ApiClient,
    Concept2ApiError,
    Concept2AuthError,
    Concept2RateLimitedError,
    Concept2ServerError,
)
from .const import (
    CONF_FULL_HISTORY_SYNC,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    EVENT_NEW_RESULT,
    FULL_RESYNC_INTERVAL_HOURS,
    LIFETIME_MILESTONE_METERS,
    MAX_FULL_SYNC_PAGES,
    MAX_RESULTS_PAGE_SIZE,
    SEASON_START_DAY,
    SEASON_START_MONTH,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

# Backoff schedule for HTTP 429/5xx - DataUpdateCoordinator does not provide
# exponential backoff on its own (design doc §4.3), so this is implemented
# here: consecutive failures push _backoff_until further out, and
# _async_update_data skips the actual API call (raising UpdateFailed
# immediately) until that time passes.
_BASE_BACKOFF_SECONDS = 60
_MAX_BACKOFF_SECONDS = 3600


@dataclass
class Concept2Data:
    """Snapshot of everything the entities need, computed fresh each update."""

    last_result: dict[str, Any] | None = None
    totals: dict[str, Any] = field(default_factory=dict)
    current_challenge: dict[str, Any] | None = None
    upcoming_challenge: dict[str, Any] | None = None
    last_synced_at: str | None = None


def _parse_result_date(result: dict[str, Any]) -> date:
    return datetime.strptime(result["date"], "%Y-%m-%d %H:%M:%S").date()


def _is_valid_result(result: Any) -> bool:
    """Treat all API responses as untrusted input (C4 / OWASP A03).

    Checks "date" is a str explicitly (rather than catching TypeError from
    strptime) so this only ever needs a single exception type - a bare
    `except (ValueError, TypeError):` reads as a Python-2-era mistake, and
    at least one ruff version strips its parentheses back out on format,
    silently reintroducing that look every time the file gets formatted.
    """
    if not isinstance(result, dict):
        return False
    if "id" not in result or "date" not in result or "distance" not in result:
        return False
    if not isinstance(result["date"], str):
        return False
    try:
        _parse_result_date(result)
    except ValueError:
        return False
    return True


def _season_start(today: date) -> date:
    if today.month >= SEASON_START_MONTH:
        return date(today.year, SEASON_START_MONTH, SEASON_START_DAY)
    return date(today.year - 1, SEASON_START_MONTH, SEASON_START_DAY)


def _compute_streak(workout_dates: set[date], today: date) -> int:
    """Consecutive days with a workout, ending today or (if none yet) yesterday."""
    if today in workout_dates:
        cursor = today
    elif (today - timedelta(days=1)) in workout_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while cursor in workout_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


class Concept2Coordinator(DataUpdateCoordinator[Concept2Data]):
    """Coordinates polling, local storage, and aggregate computation."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: Concept2ApiClient
    ) -> None:
        scan_interval_minutes = entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval_minutes),
        )
        self.entry = entry
        self.client = client
        self._store: Store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        self._results: dict[str, dict[str, Any]] = {}
        self._last_synced_at: str | None = None
        self._last_full_sync_at: datetime | None = None
        self._consecutive_failures = 0
        self._backoff_until: datetime | None = None

    @property
    def diagnostics_data(self) -> dict[str, Any]:
        """Internal state useful for diagnostics/support (T12)."""
        return {
            "last_synced_at": self._last_synced_at,
            "last_full_sync_at": (
                self._last_full_sync_at.isoformat() if self._last_full_sync_at else None
            ),
            "consecutive_failures": self._consecutive_failures,
            "result_count": len(self._results),
        }

    async def async_setup(self) -> None:
        """Load the local result store. Call once, before the first refresh."""
        stored = await self._store.async_load()
        if stored:
            self._results = stored.get("results", {})
            self._last_synced_at = stored.get("last_synced_at")
            last_full_sync = stored.get("last_full_sync_at")
            self._last_full_sync_at = (
                dt_util.parse_datetime(last_full_sync) if last_full_sync else None
            )

    async def _async_save_store(self) -> None:
        await self._store.async_save(
            {
                "results": self._results,
                "last_synced_at": self._last_synced_at,
                "last_full_sync_at": (
                    self._last_full_sync_at.isoformat()
                    if self._last_full_sync_at
                    else None
                ),
            }
        )

    async def _async_update_data(self) -> Concept2Data:
        if self._backoff_until and dt_util.utcnow() < self._backoff_until:
            raise UpdateFailed(
                f"Backing off the Concept2 API until {self._backoff_until.isoformat()}"
            )

        # Captured before _async_sync_results() runs, since it overwrites
        # _last_synced_at - this must reflect "has this account ever synced
        # before" (durable, survives reload/restart via the Store), not an
        # in-memory flag that resets on every coordinator reconstruction.
        was_first_sync = self._last_synced_at is None

        try:
            new_ids = await self._async_sync_results()
            current_challenge, upcoming_challenge = await self._async_sync_challenges()
        except Concept2AuthError as err:
            raise ConfigEntryAuthFailed("Concept2 token invalid or revoked") from err
        except (Concept2RateLimitedError, Concept2ServerError) as err:
            self._register_failure(retry_after=getattr(err, "retry_after", None))
            raise UpdateFailed(str(err)) from err
        except Concept2ApiError as err:
            raise UpdateFailed(str(err)) from err

        self._consecutive_failures = 0
        self._backoff_until = None
        await self._async_save_store()

        totals = self._compute_totals()

        if not was_first_sync:
            for result_id in new_ids:
                self._async_fire_new_result_event(result_id, totals)

        return Concept2Data(
            last_result=self._most_recent_result(),
            totals=totals,
            current_challenge=current_challenge,
            upcoming_challenge=upcoming_challenge,
            last_synced_at=self._last_synced_at,
        )

    def _register_failure(self, *, retry_after: float | None) -> None:
        self._consecutive_failures += 1
        backoff_seconds = (
            retry_after
            if retry_after is not None
            else min(
                _MAX_BACKOFF_SECONDS,
                _BASE_BACKOFF_SECONDS * (2 ** (self._consecutive_failures - 1)),
            )
        )
        self._backoff_until = dt_util.utcnow() + timedelta(seconds=backoff_seconds)

    async def _async_fetch_pages(self, **filters: Any) -> list[dict[str, Any]]:
        """Walk all pages for a filter set (T09 - every result processed once)."""
        results: list[dict[str, Any]] = []
        page = 1
        while True:
            payload = await self.client.async_get_results(
                number=MAX_RESULTS_PAGE_SIZE, page=page, **filters
            )
            results.extend(payload["data"])
            pagination = payload.get("meta", {}).get("pagination", {})
            total_pages = pagination.get("total_pages", 1)
            if page >= total_pages or page >= MAX_FULL_SYNC_PAGES:
                break
            page += 1
        return results

    def _due_for_reconciliation(self) -> bool:
        """Whether it's time to re-check for upstream deletes (§4.1.1)."""
        if not self._results:
            return False
        if self._last_full_sync_at is None:
            return True
        return dt_util.utcnow() - self._last_full_sync_at > timedelta(
            hours=FULL_RESYNC_INTERVAL_HOURS
        )

    def _earliest_known_date(self) -> str:
        return min(result["date"] for result in self._results.values())

    async def _async_sync_results(self) -> set[str]:
        """Fetch new/updated/deleted results; return ids that are genuinely new.

        Only genuinely new ids are returned (and later fire concept2_new_result,
        F4) - edits to an id we already had are folded into the store and
        reflected in totals/last-workout on the next read, but do not fire
        the event. F4 says "when a new result is detected", not "changed".
        """
        is_first_sync = self._last_synced_at is None

        if is_first_sync and self.entry.data.get(CONF_FULL_HISTORY_SYNC):
            fetched = await self._async_fetch_pages()
            self._last_full_sync_at = dt_util.utcnow()
        elif is_first_sync:
            payload = await self.client.async_get_results(number=MAX_RESULTS_PAGE_SIZE)
            fetched = payload["data"]
            # Start the reconciliation clock now, even though this wasn't a
            # full sync - otherwise _due_for_reconciliation (which treats
            # None as "overdue") would trigger one on the very next poll
            # instead of after FULL_RESYNC_INTERVAL_HOURS.
            self._last_full_sync_at = dt_util.utcnow()
        elif self._due_for_reconciliation():
            known_ids = set(self._results)
            earliest = self._earliest_known_date()
            fetched = await self._async_fetch_pages(from_=earliest)
            fetched_ids = {
                str(result["id"]) for result in fetched if _is_valid_result(result)
            }
            for deleted_id in known_ids - fetched_ids:
                del self._results[deleted_id]
            self._last_full_sync_at = dt_util.utcnow()
        else:
            fetched = await self._async_fetch_pages(updated_after=self._last_synced_at)

        new_ids: set[str] = set()
        for result in fetched:
            if not _is_valid_result(result):
                _LOGGER.warning(
                    "Skipping malformed result from Concept2 API (id=%s)",
                    result.get("id", "unknown")
                    if isinstance(result, dict)
                    else "unknown",
                )
                continue
            result_id = str(result["id"])
            if result_id not in self._results:
                new_ids.add(result_id)
            self._results[result_id] = result

        self._last_synced_at = dt_util.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return new_ids

    async def _async_sync_challenges(
        self,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        current = await self.client.async_get_current_challenges()
        upcoming = await self.client.async_get_upcoming_challenges()
        return (current[0] if current else None, upcoming[0] if upcoming else None)

    def _most_recent_result(self) -> dict[str, Any] | None:
        if not self._results:
            return None
        return max(self._results.values(), key=lambda r: r["date"])

    def _compute_totals(self) -> dict[str, Any]:
        today = dt_util.now().date()
        week_start = today - timedelta(days=today.isoweekday() - 1)
        month_start = today.replace(day=1)
        season_start = _season_start(today)

        meters_today = meters_this_week = meters_this_month = 0
        meters_this_season = meters_lifetime = 0
        workouts_this_week = workouts_this_month = 0
        calories_this_month = 0
        workout_dates: set[date] = set()

        for result in self._results.values():
            result_date = _parse_result_date(result)
            distance = result.get("distance", 0) or 0
            calories = result.get("calories_total", 0) or 0
            workout_dates.add(result_date)

            meters_lifetime += distance
            if result_date >= season_start:
                meters_this_season += distance
            if result_date >= month_start:
                meters_this_month += distance
                workouts_this_month += 1
                calories_this_month += calories
            if result_date >= week_start:
                meters_this_week += distance
                workouts_this_week += 1
            if result_date == today:
                meters_today += distance

        return {
            "meters_today": meters_today,
            "meters_this_week": meters_this_week,
            "meters_this_month": meters_this_month,
            "meters_this_season": meters_this_season,
            "meters_lifetime": meters_lifetime,
            "workouts_this_week": workouts_this_week,
            "workouts_this_month": workouts_this_month,
            "calories_this_month": calories_this_month,
            "workout_streak": _compute_streak(workout_dates, today),
            "workout_done_today": today in workout_dates,
        }

    def _async_fire_new_result_event(
        self, result_id: str, totals: dict[str, Any]
    ) -> None:
        """Fire concept2_new_result - never called during the initial sync (F4)."""
        result = self._results[result_id]
        distance = result.get("distance", 0) or 0
        lifetime_before = totals["meters_lifetime"] - distance
        milestone_crossed = (
            lifetime_before // LIFETIME_MILESTONE_METERS
            != totals["meters_lifetime"] // LIFETIME_MILESTONE_METERS
        )

        today = dt_util.now().date()
        season_start = _season_start(today)
        season_distances = [
            r.get("distance", 0) or 0
            for r in self._results.values()
            if _parse_result_date(r) >= season_start
        ]
        longest_row_this_season = distance >= max(season_distances, default=0)

        self.hass.bus.async_fire(
            EVENT_NEW_RESULT,
            {
                "result": result,
                "milestone_crossed": milestone_crossed,
                "longest_row_this_season": longest_row_this_season,
            },
        )
