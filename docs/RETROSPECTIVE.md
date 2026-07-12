# Retrospective — v1.0.x

Written after Gate 4 closed in full (`v1.0.2`, 2026-07-12). Purpose: capture
what actually happened during this build so future work on this integration
- and future HACS integrations built the same way - starts from real lessons,
not just good intentions. Kept factual and specific; a lessons file that's
just praise isn't useful to anyone reading it later.

## What went well

- **Evidence over assertion, every time.** Every claim of "this works" in
  README/SECURITY/CHANGELOG is backed by something checked, not assumed: a
  `curl` from the actual HA host, a real diagnostics export, a real event
  payload pasted from Developer Tools, a regression test proven to fail
  without its fix (not just added and left green). This is the single
  habit most worth carrying forward.
- **Stage-gate discipline held under pressure to move faster.** Multiple
  points (D5, D6) required explicitly stopping to flag a conflict or a
  tradeoff rather than silently proceeding - even when "just ship it" would
  have been easier. The design doc's decision log (D1-D6) means anyone
  reading it later can reconstruct *why*, not just *what*.
- **Docs treated as load-bearing, not decorative.** README/SECURITY/CHANGELOG
  were updated in the same commit as the behavior they describe, every time
  - including walking back overclaims (e.g. "not a testing is done v1.0.0"
  language removed only once every acceptance test was actually confirmed
  live, not before).

## Technical lessons

- **Never track "is this the first run" in an in-memory flag.** The
  `concept2_new_result` silent-failure bug (fixed in `v0.2.4-alpha`) existed
  because `_initial_sync_done` reset to `False` on every coordinator
  reconstruction (any reload, any HA restart) - not just a true first-ever
  install. The durable signal was already there (`_last_synced_at is None`,
  persisted via the Store) but wasn't being used. General rule for any HA
  coordinator: if a piece of state needs to survive reload/restart, it must
  come from something persisted, never a plain instance attribute.
- **Don't trust an external API's documentation over live behavior.**
  Concept2's challenge endpoints mislabel `Content-Type` as `text/html` even
  for JSON bodies, and return a bare `{}` (not `{"data": []}`) for "no
  current challenge" - neither matches their own published docs. Found only
  by making the error messages actually include the underlying exception
  (`v0.2.1-alpha`), then reading the real error instead of a generic one.
  General rule: when wrapping a third-party API client's errors, never
  discard the original exception's message - it's the only way to diagnose
  a live failure without re-instrumenting and re-shipping first.
- **GitHub's archive-by-branch-name URL pattern silently breaks for
  commit-based installs.** HACS's un-tagged auto-update path requested
  `archive/refs/heads/<commit-sha>.zip`, which 404s (that path is for branch
  names, not SHAs). A tagged release fixes this permanently; it's not a
  transient bug that fixes itself.
- **aiohttp's `response.json()` strict content-type check will break on
  real-world APIs that don't follow their own spec.** `content_type=None`
  is the right escape hatch when the body is genuinely JSON but mislabeled
  - not a reason to avoid JSON parsing.

## Process lessons

- **The reload-then-test instinct can hide bugs.** The very first live test
  of `concept2_new_result` used "reload to force an immediate check" as a
  shortcut - which is exactly what exposed the `_initial_sync_done` bug.
  Lucky in this case (the shortcut caused the discovery), but the general
  lesson is: a "fast path" for testing can behave differently from the real
  code path (a natural scheduled poll) - verify both when either could
  plausibly diverge.
- **Small commits, gated on CI, before tagging - not after.** Every release
  in this project's history followed the same shape: change → local
  verify (pytest + ruff) → commit → push → wait for all 5 CI checks green →
  *then* tag → *then* GitHub release. Tagging first and hoping CI passes
  would have meant shipping releases that fail their own validation.
- **A version bump is cheap; use it to signal, not just to ship code.**
  Several releases in this history (`v0.2.3-alpha`, `v1.0.1`, `v1.0.2`) had
  zero functional code changes - they existed purely to make a documentation
  or status change visible to HACS/GitHub's "latest release" resolution.
  That's a legitimate use of a version bump, not overhead.
