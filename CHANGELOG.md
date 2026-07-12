# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Nothing yet.

## [0.2.5-alpha] - 2026-07-12

### Added

- "Last synced" timestamp sensor - integration health (when the coordinator
  last successfully polled Concept2), distinct from workout-data sensors.
  Stakeholder request while doing live Gate 4 testing.
- "Sync now" button - requests an immediate coordinator refresh
  (`coordinator.async_request_refresh()`) without reloading the whole
  config entry. Lighter than the integration Reload workaround, and
  correctly respects the coordinator's own rate-limit backoff since it goes
  through the same `_async_update_data()` path as a scheduled poll.
- README now states the polling cadence explicitly (15 min default, 10 min
  minimum) and that this is a `GET` request on a timer, not a Concept2
  push/webhook - previously only the minimum was mentioned, in Options.

## [0.2.4-alpha] - 2026-07-12

### Fixed

- **`concept2_new_result` could silently never fire for a real user.**
  `_initial_sync_done` was a plain in-memory flag on the coordinator object,
  reset to `False` every time that object was reconstructed - which happens
  on every integration reload and every Home Assistant restart, not just a
  true first-ever install. `_last_synced_at`, `_results`, etc. are correctly
  persisted and reloaded from the Store; this flag wasn't, so the first
  refresh after any reload treated itself as "the initial sync" and
  suppressed the event even for a genuinely new result. Found live: a
  stakeholder did a real row, reloaded the integration to force an immediate
  poll, and the event never fired - confirmed by reverting the fix and
  re-running the new regression test, which fails without it (0 events
  instead of 1). Now derived from `_last_synced_at is None`, captured before
  the sync call that overwrites it - durable across reload/restart, matching
  the actual intent ("initial full-history sync must not fire events", not
  "every reload's first poll must not fire events").

## [0.2.3-alpha] - 2026-07-12

No functional/code changes from 0.2.2-alpha - documentation only.

### Changed

- README reorganized for a new reader finding this repo cold: What this is →
  Sensors (grouped, not one dense paragraph) → Options → Screenshots → What
  this is not → Requirements → Installation → everything else.
- **This is the first release not marked a GitHub pre-release.** Auth, full
  history sync, and real sensor/challenge data are confirmed working against
  a real account (see the warning at the top of README), so HACS now offers
  this as a normal update without needing "Show beta versions" enabled.
  Still explicitly labeled `alpha` and still not a "testing is done" claim:
  `concept2_new_result` firing on a genuinely new workout, and totals holding
  up over a longer stretch of time, are unconfirmed - that's Gate 4, not this
  release.

## [0.2.2-alpha] - 2026-07-12

### Fixed

- The actual root cause behind the `ConfigEntryNotReady` loop on
  `/api/challenges/current`, now visible thanks to 0.2.1-alpha's better
  error message: `ContentTypeError: 200, message='Attempt to decode JSON
  with unexpected mimetype: text/html; charset=utf-8'`. Confirmed live
  (2026-07-12) against Concept2's production API, even with an explicit
  `Accept: application/json` sent: Concept2 mislabels the challenge
  endpoints' `Content-Type` header, and represents "no current/upcoming
  challenge" as a bare `{}` rather than `{"data": []}`, neither of which
  matches the documentation this client was built against (constraint C2).
  `_get()` now parses JSON without aiohttp's strict mimetype check and
  treats an empty `{}` as "no data" - opt-in per endpoint via a new
  `allow_empty` parameter, so the authenticated results/user endpoints
  still reject a genuinely malformed response exactly as before.

## [0.2.1-alpha] - 2026-07-11

### Fixed

- `api.py`'s network/timeout error wrapping discarded the underlying aiohttp
  exception's own message, leaving only a generic "Network error calling
  Concept2 API for {path}" with no way to tell DNS failure, connection
  refused, TLS error, or anything else apart. Found while live-debugging a
  real `ConfigEntryNotReady` retry loop on `/api/challenges/current` where
  `curl` from the same Home Assistant host succeeded cleanly, meaning the
  actual cause was in the aiohttp/Python layer, not the network path — and
  the wrapped message gave no way to tell what. The underlying error is now
  included in the message; token-leak test coverage extended to confirm it
  still can't leak a token through this path.

## [0.2.0-alpha] - 2026-07-11

Tagged specifically to fix HACS's commit-based update delivery, which was
requesting a GitHub archive URL shaped for branch names against a commit SHA
and reliably 404'ing (confirmed against a real test instance's logs). **Not**
a "manual testing is done" release - Gate 4 acceptance testing is still in
progress, not complete; see the warning in README.md.

### Added

- Personal access token config flow (D5) — generate a token at your Concept2
  profile (Edit Profile → Applications → Concept2 Logbook API) and paste it
  in. Replaces an earlier OAuth2 Authorization Code design (built, then
  superseded before this tag - see the design doc's §4.2/D5 for why).
  Reauth on token revocation/expiry, `wrong_account` protection if a second
  entry is authenticated with a different Concept2 account's token.
- Thin async Concept2 API client (results, user profile, challenges) — read-only,
  no write-capable methods exist in the code. Wraps aiohttp connection/timeout
  failures into a typed error so `cannot_connect` means what it says.
- `DataUpdateCoordinator` with a local result store so aggregate totals recompute
  correctly when a historical result is edited or deleted upstream, and custom
  exponential backoff on HTTP 429/5xx (not provided by the coordinator base class).
- Sensors: last workout (distance, time, average pace, stroke rate, calories,
  average heart rate, drag factor, date), computed totals (meters today/this
  week/this month/this season/lifetime, workouts this week/month, calories this
  month, workout streak), a "workout done today" binary sensor, and current/upcoming
  Concept2 challenge sensors.
- `concept2_new_result` event, fired only for genuinely new results (never during
  the initial sync, never for edits to an existing result), carrying the result
  payload plus a lifetime-milestone flag and a "longest row this season" flag.
- Options flow for the polling interval, with a floor to stay a reasonable API
  citizen.
- Diagnostics export with token/identifier redaction via Home Assistant's own
  `async_redact_data` helper.
- Full English translations for the config flow, options flow, and all entities.
- CI/security hardening: 100% test coverage, CodeQL code scanning, GitHub
  secret scanning + push protection, Dependabot security updates, private
  vulnerability reporting, least-privilege permissions on every workflow.

### Known limitations

- Deletion detection lags up to ~24h behind (bounded periodic reconciliation, not
  real-time) — Concept2's polling API has no "deleted items" feed.
- Workout dates are assumed to be in Home Assistant's local timezone.
- Not submitted to the HACS default store yet (custom-repository install only).
- A personal access token's scope is set by Concept2's own page at generation
  time and cannot be inspected or restricted by this integration's code - a
  narrower guarantee than the OAuth2 design it replaced (see SECURITY.md).
- Integration icon is a plain placeholder, not a designed logo.

### Not yet done

- Full manual acceptance testing on a real Home Assistant instance / real
  Concept2 account, including a real workout triggering `concept2_new_result`
  (Gate 4) - config-flow authorization has been confirmed working, but totals
  accumulating over time and the event firing have not.
- Screenshots.
- HACS default-store submission, a non-placeholder icon, a v1.0.0 release (Gate 5).
