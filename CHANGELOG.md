# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Nothing yet.

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
