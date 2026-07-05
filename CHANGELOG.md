# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

No version has been tagged/released yet — see the README's
["No releases yet"](README.md#no-releases-yet) note. Everything below is unreleased,
built but not yet manually verified against a real Home Assistant instance or a real
Concept2 account (the project's own "Gate 4").

## [Unreleased]

### Added

- OAuth2 Authorization Code config flow via Home Assistant's Application
  Credentials, with reauth on token expiry/revocation.
- Thin async Concept2 API client (results, user profile, challenges) — read-only,
  no write-capable methods exist in the code.
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

### Known limitations

- Deletion detection lags up to ~24h behind (bounded periodic reconciliation, not
  real-time) — Concept2's polling API has no "deleted items" feed.
- Workout dates are assumed to be in Home Assistant's local timezone.
- Not submitted to the HACS default store yet (custom-repository install only).

### Not yet done

- Manual acceptance testing on a real Home Assistant instance / real Concept2
  account (Gate 4).
- Screenshots (need a real running instance to capture honestly — see README).
- A tagged release (Gate 5).
