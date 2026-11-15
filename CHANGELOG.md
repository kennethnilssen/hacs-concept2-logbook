# Changelog

All notable changes to this project are in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Nothing yet.

## [1.0.2] - 2026-07-12

### Changed

- No code change. A test with a real revoked token confirmed the reauthentication.
  Home Assistant asks for a new token, and the integration continues after you paste it.

## [1.0.1] - 2026-07-12

### Added

- `docs/example-dashboard.yaml`: an example dashboard that uses only standard Home
  Assistant cards. It renders with real data on a live instance.

## [1.0.0] - 2026-07-12

First stable release. The code is the same as in `0.2.5-alpha`. The main functions work
on one real Home Assistant instance and one real Concept2 account: setup with a token,
the sync of the full history, the sensors, the challenges, the event
`concept2_new_result` and the diagnostics export.

## Before 1.0.0 (alpha)

The alpha releases `0.2.0` to `0.2.5` added the functions below and fixed these errors.

### Added

- Setup with a personal access token, and reauthentication if you revoke the token.
- Sensors for the last workout, the totals, the streak, the current challenge and the
  upcoming challenge. The binary sensor "Workout done today".
- The event `concept2_new_result`. It does not fire during the first sync or for a
  changed result.
- The sensor "Last synced" and the button "Sync now".
- An options flow for the polling interval (10 minutes or more).
- A diagnostics export that redacts the token and personal data.

### Fixed

- The event `concept2_new_result` did not fire for the first new result after a
  reload or a restart of Home Assistant.
- The setup stopped with the "Network error" message for `/api/challenges/current`.
  Concept2 sends this response with the wrong content type (`text/html`) and sends `{}`
  when no challenge exists. The integration now accepts both.
- A network error message did not show the cause. It now shows it, without the token.
- HACS could not install an update without a tagged release. Each version is now tagged.
