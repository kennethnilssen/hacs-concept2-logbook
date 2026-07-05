# Concept2 Logbook — Home Assistant Integration

[![Test](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/test.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/test.yml)
[![Lint](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/lint.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/lint.yml)
[![Hassfest](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hassfest.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hassfest.yml)
[![HACS validation](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hacs.yml/badge.svg)](https://github.com/kennethnilssen/hacs-concept2-logbook/actions/workflows/hacs.yml)

Connects your [Concept2 Logbook](https://log.concept2.com) account to Home Assistant
over the official Concept2 API, and exposes your workout results as sensors and an
automation event. Read-only — it never writes anything back to your Concept2 account.

> [!WARNING]
> **Untested and AI-written. Read this before installing.**
> This integration was built end-to-end by [Claude Code](https://claude.com/claude-code)
> (an AI coding agent) under human supervision — every line was reviewed, but it has
> **not yet been run against a real Home Assistant instance or a real Concept2
> account**. It's unit-tested (100% line coverage, CI green — see badges above),
> but unit tests mock the API; nobody has actually authorized it, watched a real
> sensor populate, or rowed a workout and seen the event fire. That manual
> verification (the project's own "Gate 4") hasn't happened yet.
>
> There are also **no tagged releases yet** — see [No releases yet](#no-releases-yet)
> below before you install. Use at your own risk, expect rough edges, and please
> [open an issue](../../issues) if something breaks.

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
- Your **own** Concept2 API client — Concept2 requires every application to register
  its own OAuth client (no shared/default credentials are bundled with this
  integration, by design — see [SECURITY.md](SECURITY.md)). Register one at the
  [Concept2 API Key portal](https://log.concept2.com/developers/keys); this is free
  and takes a couple of minutes. The integration's setup screen tells you exactly
  what redirect URI to enter.
- [HACS](https://hacs.xyz) installed (recommended), or willingness to copy files in
  manually.

## Installation

### No releases yet

This repository doesn't have a tagged release (that happens at the project's "Gate
5", after manual testing). Until then, HACS will install directly from the `main`
branch — effectively the latest commit, not a stable pinned version. It can change
or break between the time you install it and the time you next update it. If you'd
rather wait for a tagged `v1.0.0`, [watch the repo](../../subscription) or check the
[Releases page](../../releases) before installing.

### Via HACS (recommended)

1. In Home Assistant, go to **HACS**.
2. Click the **⋮** (three dots) in the top right → **Custom repositories**.
3. Add this repository's URL, category **Integration**:
   `https://github.com/kennethnilssen/hacs-concept2-logbook`
4. Find **Concept2 Logbook** in HACS and click **Download**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration**, search for
   **Concept2 Logbook**.
7. The setup screen will tell you where to register your API client and what
   redirect URI to use (see [Requirements](#requirements) above). Enter your client
   ID/secret under **Settings → Application Credentials** when prompted, then
   authorize with your Concept2 account.
8. You'll be asked whether to sync your full workout history now (accurate lifetime
   totals immediately, but slower on first setup) or start fresh from today (totals
   grow over time instead).

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

None yet, honestly — screenshots would need a real running Home Assistant instance
with a real Concept2 account authorized against it, which hasn't happened yet (see
the warning at the top). Adding fake/mocked-up screenshots here would be more
misleading than having none. Real ones will replace this section once manual testing
happens.

## Known v1 limitations

- Deleting a workout on Concept2's side isn't detected instantly — it's caught on a
  periodic reconciliation (up to ~24h later), since Concept2's polling API has no
  "deleted items" feed (only its webhook does, which is out of scope for v1).
- Workout dates are assumed to be in Home Assistant's local timezone (Concept2's API
  doesn't reliably return one).
- Not yet submitted to the HACS default store — install as a custom repository (above).

## Security

- OAuth2 Authorization Code flow via Home Assistant's Application Credentials — you
  authorize with your own Concept2 account and can revoke access at any time from
  Concept2 Settings → Applications.
- Requests only `user:read results:read` scopes — nothing else.
- No credentials are ever stored in this repository or logged.
- See [SECURITY.md](SECURITY.md) for the full threat model and OWASP alignment.

## Attribution

Built with [Claude Code](https://claude.com/claude-code), human-reviewed,
security-focused — see [CLAUDE.md](CLAUDE.md) for the working agreement this project
was built under, and [concept2-ha-integration-design.md](concept2-ha-integration-design.md)
for the full design, scope, and test plan. See [CHANGELOG.md](CHANGELOG.md) for
what's actually been built so far.

## License

MIT — see [LICENSE](LICENSE).
