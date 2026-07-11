<p align="center">
  <img src="custom_components/concept2_logbook/brand/icon.png" width="96" height="96" alt="Concept2 Logbook icon (plain placeholder, not a designed logo)">
</p>

# Concept2 Logbook — Home Assistant Integration

[![Test](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/test.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/test.yml)
[![Lint](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/lint.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/lint.yml)
[![Hassfest](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hassfest.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hacs.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hacs.yml)

Connects your [Concept2 Logbook](https://log.concept2.com) account to Home Assistant
over the official Concept2 API, and exposes your workout results as sensors and an
automation event. Read-only — it never writes anything back to your Concept2 account.

> [!WARNING]
> **AI-written, testing in progress. Read this before installing.**
> This integration was built end-to-end by [Claude Code](https://claude.com/claude-code)
> (an AI coding agent) under human supervision — every line was reviewed. It's
> unit-tested (100% line coverage, CI green — see badges above), and the config
> flow (personal access token authorization) has been confirmed working against
> a real Home Assistant instance and a real Concept2 account. Full manual
> acceptance testing - a workout actually appearing, the event firing, totals
> accumulating over time - (the project's own "Gate 4") is still in progress,
> not complete.
>
> There's a [pre-release](../../releases) (`v0.2.0-alpha`) so HACS can deliver
> updates at all - see [Pre-release only](#pre-release-only---not-a-testing-is-done-signal)
> below before you install. This is **not** a "testing is done" v1.0.0. Use at
> your own risk, expect rough edges, and please [open an issue](../../issues)
> if something breaks.

## What this is

- Polls the Concept2 API periodically for your logged results (RowErg, SkiErg, BikeErg
  — anything Concept2 tracks) and exposes them as Home Assistant sensors: last
  workout details, computed totals (today/week/month/season/lifetime), a workout
  streak, and current/upcoming Concept2 challenges.
- Fires a `concept2_new_result` event when a genuinely new result appears, so you can
  trigger automations (e.g. a TTS announcement, a light scene) on a new row.
- Optional one-time full history sync on setup, for accurate lifetime totals from day
  one instead of growing from install date.

## What this is *not*

- **Not live telemetry.** It reads results after they sync to the Concept2 Logbook —
  it does not talk to your PM5 over Bluetooth while you're rowing. If you want
  live stroke-by-stroke data on the wall while rowing, this isn't that; look at the
  existing PM5 Bluetooth integrations instead.
- **Not able to write anything.** No scopes, no code path, can create/edit/delete
  nothing in your Concept2 account.

## Requirements

- A Concept2 Logbook account.
- Your **own** personal access token, generated in a few clicks at
  **log.concept2.com → Profile → Edit Profile → Applications → Concept2 Logbook API**.
  No app registration, no client ID/secret, no redirect URI to configure — it's a
  single token string. It stays valid until you revoke it on that same page. (This
  integration is strictly read-only; per Concept2's own docs, personal-use apps that
  only read data are meant to use this token rather than register a full OAuth
  client, which is the path for apps distributed to multiple users.)
- [HACS](https://hacs.xyz) installed (recommended), or willingness to copy files in
  manually.

## Installation

### Pre-release only - not a "testing is done" signal

[`v0.2.0-alpha`](../../releases) exists purely so HACS can actually deliver
updates — without any tag, HACS was requesting a GitHub archive URL shaped for
branch names against a commit SHA, which reliably 404'd (confirmed against a
real test instance's logs, not assumed). It is **not** a v1.0.0 "manual testing
is done" release — that's still Gate 5, after Gate 4's manual acceptance
testing, which hasn't happened yet (see the warning at the top). Expect more
pre-releases as testing continues before an eventual `v1.0.0`.

### Via HACS (recommended)

1. In Home Assistant, go to **HACS**.
2. Click the **⋮** (three dots) in the top right → **Custom repositories**.
3. Add this repository's URL, category **Integration**:
   `https://github.com/kennethnilssen/hacs-concept2-logbook`
4. Find **Concept2 Logbook** in HACS and click **Download**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration**, search for
   **Concept2 Logbook**.
7. Generate a personal access token at
   **log.concept2.com → Profile → Edit Profile → Applications → Concept2 Logbook API**
   (see [Requirements](#requirements) above), then paste it into the setup form.
8. You'll be asked whether to sync your full workout history now (accurate lifetime
   totals immediately, but slower on first setup) or start fresh from today (totals
   grow over time instead).

### Revoking access

Go back to **log.concept2.com → Profile → Edit Profile → Applications** and revoke
the token there at any time. Home Assistant will detect this on its next poll and
prompt you to reauthenticate (paste a new token) rather than fail silently.

### Manual (without HACS)

1. Copy `custom_components/concept2_logbook` from this repo into your Home
   Assistant config's `custom_components/` folder.
2. Restart Home Assistant.
3. Continue from step 6 above.

## Sensors

Last-workout distance/time/pace/stroke rate/calories/heart rate/drag factor/date,
computed totals (meters today/this week/this month/this season/lifetime, workouts
this week/month, calories this month, workout streak), a "workout done today" binary
sensor, and current/upcoming Concept2 challenge sensors. Full detail in the design
doc (`concept2-ha-integration-design.md`) §3.1 F3.

## Options

**Settings → Devices & Services → Concept2 Logbook → Configure** lets you change the
polling interval (minimum 10 minutes, to stay a good citizen of Concept2's API).

## Screenshots

None yet, honestly — the config flow has now run against a real instance and
account, but nobody's captured screenshots of it yet, and sensors haven't
populated with real workout data (see the warning at the top). Adding
fake/mocked-up screenshots here would be more misleading than having none.
Real ones will replace this section as manual testing continues.

## Known v1 limitations

- Deleting a workout on Concept2's side isn't detected instantly — it's caught on a
  periodic reconciliation (up to ~24h later), since Concept2's polling API has no
  "deleted items" feed (only its webhook does, which is out of scope for v1).
- Workout dates are assumed to be in Home Assistant's local timezone (Concept2's API
  doesn't reliably return one).
- Not yet submitted to the HACS default store — install as a custom repository (above).
- The integration icon (`custom_components/concept2_logbook/brand/icon.png`) is a
  plain placeholder, not a designed logo — nobody's done branding work on this yet.

## Security

- Personal access token authentication (D5) — you generate your own token at your
  Concept2 profile and can revoke it at any time from that same page.
- Read-only: no write scopes requested, no code path capable of writing to Concept2.
  Talks to the production Concept2 API directly — per Concept2's own docs, read-only
  personal-use apps aren't required to develop against a separate dev server.
- No credentials are ever stored in this repository or logged.
- **One honest limitation:** unlike a full OAuth2 client registration, this
  integration cannot see or restrict what scope your personal token actually carries
  — that's set by Concept2's own page when you generate it, not by this integration's
  code. See [SECURITY.md](SECURITY.md) for the full threat model and OWASP alignment.

## Attribution

Built with [Claude Code](https://claude.com/claude-code), human-reviewed,
security-focused — see [CLAUDE.md](CLAUDE.md) for the working agreement this project
was built under, and [concept2-ha-integration-design.md](concept2-ha-integration-design.md)
for the full design, scope, and test plan. See [CHANGELOG.md](CHANGELOG.md) for
what's actually been built so far.

## License

MIT — see [LICENSE](LICENSE).
