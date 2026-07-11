# Concept2 Logbook — Home Assistant HACS Integration
## Project Charter, Solution Design & Test Plan (Stage-Gate Model)

**Version:** 0.3 (Gate 1 closed; Gate 2 design reviewed, pending stakeholder sign-off)
**Date:** 2026-07-05
**Prepared with:** Claude (Anthropic)
**Repository name (proposed):** `hacs-concept2-logbook`
**Integration domain:** `concept2_logbook`
**Display name:** Concept2 Logbook
**Tagline:** This integration connects Concept2 Logbook to Home Assistant over API using the official Concept2 API protocol.

---

## 1. Project Concept (Gate 0 — Idea)

Build a custom Home Assistant integration, distributed through HACS, that connects a
user's Concept2 Logbook account to Home Assistant. The integration fetches workout
results and statistics from the official Concept2 Logbook API and exposes them as
Home Assistant entities (sensors and events), enabling:

- Visible metrics on Lovelace dashboards (last workout, totals, trends).
- Automations triggered by new results or milestones (e.g. TTS announcement when a
  personal best or distance goal is achieved).

**Explicitly out of scope:** live/real-time rowing telemetry. Live data is visible on
the PM5 while rowing and is served by existing Bluetooth solutions. This integration
handles *logged results only*, after they sync to the Concept2 Logbook.

**Gate 0 exit criteria:** Stakeholder confirms concept and out-of-scope boundary. ✅ (confirmed in chat)

---

## 2. Binding Constraints (Non-Negotiable)

These constraints apply at every stage and every gate. A gate cannot be passed if any
constraint is violated.

| # | Constraint | Source of truth |
|---|------------|-----------------|
| C1 | Full compliance with HACS requirements and usage documentation | https://www.hacs.xyz/docs/use/ and HACS publishing docs |
| C2 | Full compliance with the Concept2 Logbook API documentation, terms, and approval process | https://log.concept2.com/developers/documentation/ |
| C3 | Security by design: self-service authentication, user can revoke at any time from their Concept2 profile. **Amended 2026-07-11 (D5):** v1.0 uses Concept2's personal access token (Edit Profile → Applications → Concept2 Logbook API) rather than full OAuth2 client registration - confirmed via the stakeholder's own account that the "API Key portal" client-registration flow is the app-developer path for multi-user distribution, not what an individual sees on their own profile. Scope is set by Concept2's UI at token-generation time and is **not visible or restrictable by this integration's code** (unlike the OAuth2 design, which enforced `user:read,results:read` explicitly on every token request) - a documented, accepted limitation, not a code-enforced guarantee. OAuth2 Authorization Code flow deferred to v1.x. | Concept2 API docs + OWASP + stakeholder account verification |
| C4 | Auditability: code must be transparent, reviewable, and state that it was created with Claude Code; OWASP-aligned secure coding practices throughout | OWASP ASVS / Top 10 |

---

## 3. Scope Definition (Gate 1 — Scoping)

### 3.1 In scope (v1.0)

**Functional**
- F1: Config flow in the HA UI (no YAML required) that guides the user through
  self-service Concept2 authorization via OAuth2.
- F2: Periodic polling of the Concept2 Logbook API for the authenticated user's
  results, using incremental sync (`updated_after`) to minimize API load.
- F3: Sensor entities (agreed 2026-07-05, closes D1):
  - **Last workout:** distance (m), time (duration), average pace (/500m; /1000m for BikeErg),
    stroke rate (spm, stroke count as attribute), calories, average heart rate
    (min/max/ending as attributes), drag factor, date (timestamp). Attributes on the
    distance sensor: machine type, workout type, source, verified/ranked, comments.
  - **Totals & counters (computed locally — the API provides no ready-made totals):**
    meters today / this week (ISO week) / this month / this season (Concept2 season =
    May 1 – April 30) / lifetime; workouts this week / this month; calories this month;
    workout streak (consecutive days).
  - **Binary sensor:** "Workout done today".
  - **Challenges (public endpoints, no auth):** current challenge and upcoming
    challenge (name as state; end date, description as attributes).
  - Lifetime totals require an optional full-history sync on first setup (paginated,
    250 results/page); user opts in during config flow.
  - Primary machine type: **RowErg** (stakeholder hardware: RowErg PM5 Standard).
    Design remains machine-type-aware so SkiErg/BikeErg data creates parallel sensors
    automatically if it ever appears.
  - Deferred to v1.1: personal bests over standard distances, per-split sensors.
- F4: An HA event (`concept2_new_result`) fired when a new result is detected,
  carrying the result payload plus computed extras (e.g. round-number lifetime
  milestone crossed, longest row this season) — this is the automation/TTS hook.
  Initial full-history sync must NOT fire events (no event storm on setup).
- F5: Reauthentication flow when tokens expire or are revoked (HA reauth pattern).
- F6: Options flow: polling interval (sane default, e.g. 10–15 min; enforce a minimum
  to be a good API citizen).

**Non-functional**
- N1: HACS-compliant repository structure (manifest.json, hacs.json, versioned GitHub
  releases, README with install/setup instructions).
- N2: Async, non-blocking code following current Home Assistant development standards
  (DataUpdateCoordinator, CoordinatorEntity, config entries).
- N3: OWASP-aligned security (see §5).
- N4: English UI strings with HA translation scaffolding (`strings.json` /
  `translations/en.json`); Norwegian translation as a stretch goal.
- N5: Attribution notice in README and source headers: built with Claude Code,
  human-reviewed, security-focused.

### 3.2 Out of scope (v1.0)

- Live PM5 telemetry (Bluetooth) — permanently out of scope for this project.
- Webhooks (real-time push of new results) — deferred to v1.1+; requires an
  externally reachable HA endpoint and adds attack surface. Polling first.
- Writing data to Concept2 (no write scopes are requested — read-only by design).
- Multi-user support in a single config entry — v1 supports one Concept2 account per
  config entry; multiple entries can be added for household members.
- Submission to the HACS *default* store — v1 ships as a HACS custom repository;
  default-store submission is a v1.x milestone once stable.

### 3.3 Stakeholder / user stories

- As a rower, I want my latest workout on my dashboard so I can see my progress at a glance.
- As a home automator, I want an event when a new result arrives so I can trigger a TTS
  announcement (e.g. "New personal record!") or light scene.
- As a security-conscious user, I want to authorize with my own Concept2 account,
  grant only read permissions, and be able to revoke access at any time.
- As an auditor/reviewer, I want to read the code and verify no credentials are logged,
  stored insecurely, or transmitted anywhere except api.concept2.com over TLS.

**Gate 1 exit criteria:** Stakeholder signs off on scope, sensor list, and deferrals.

---

## 4. Solution Design (Gate 2 — Design)

### 4.1 Architecture overview

```
Concept2 Logbook API (OAuth2, HTTPS)
        │  polling (updated_after)
        ▼
API Client (thin async wrapper, aiohttp via HA session)
        ▼
DataUpdateCoordinator (single fetch cycle, shared by all entities)
        ▼
Local result store (HA `Store` helper, JSON — raw results keyed by result id;
  see §4.1.1 — required to recompute totals correctly on edits/deletes, not
  just accumulate on new results)
        ▼
├── Sensor entities (last workout, totals — derived from the local store)
├── Event: concept2_new_result (automation hook, fired only for ids not
│   previously seen in the local store)
└── Diagnostics (redacted — for support/audit)
```

#### 4.1.1 Local result store (added on review — closes a correctness gap)

The original design implied totals (lifetime meters, season meters, streaks) would
be accumulated incrementally as new results arrive. That breaks under §4.3's own
requirement to "handle deletes/updates of results gracefully": if a historical result
is edited or deleted upstream after it was already folded into a running total, a
stateless coordinator has no way to correct that total — it only ever sees the delta
since `updated_after`.

Fix: the coordinator persists raw results (id, timestamp, distance, time, etc. — not
tokens or PII beyond what the API already returns) in a local `homeassistant.helpers.storage.Store`
file scoped to the config entry. Every poll upserts changed/new results into the store
by id and removes any the API reports deleted; **all aggregate sensors are recomputed
from the store**, not accumulated in memory. This is a few dozen lines of code, keeps
the coordinator otherwise stateless-feeling, and is the only way to make T10 (result
updated/deleted upstream) actually true for the totals sensors, not just the
last-workout sensor. See new test T15 in §6.1.

### 4.2 Authentication design (C3)

**SUPERSEDED 2026-07-11 by D5** — v1.0 uses a Concept2 personal access token
instead of the OAuth2 design below. Kept here as historical record, not deleted:
the OAuth2 design was fully built (Gate 3 step 3) and worked, but the stakeholder
confirmed via their own account that Concept2's "API Key portal" client
registration is the app-developer path for multi-user distribution, not what an
individual sees on their own profile - the personal access token is what
Concept2 actually intends here. See §4.2.1 below for the current design, and D5
in §9 for the full rationale and the accepted scope-visibility tradeoff.

- OAuth2 Authorization Code flow using Home Assistant's built-in
  `config_entry_oauth2_flow` and **Application Credentials** platform.
- Scopes requested: `user:read results:read` — nothing more (least privilege).
- Each installing user registers their own API client in the Concept2 developer
  self-service portal and enters their client ID/secret into HA's Application
  Credentials UI. Consequence: no shared secret is ever published in the repository.
- Tokens are stored by Home Assistant's config entry storage (never in plaintext
  custom files, never logged). Refresh token rotation is handled by HA's OAuth2
  session helper.
- README documents, with screenshots, the exact self-service steps including the
  Concept2 consent screen and how to revoke access (Settings → Applications).
- Development happens against the Concept2 **development server** first; switching to
  production follows Concept2's approval process (C2).
- **Redirect URI (added on review):** uses Home Assistant's standard external OAuth
  callback (`/auth/external/callback`), routed through the My Home Assistant
  redirection service for instances without a stable public HTTPS URL — the same
  mechanism HA core OAuth integrations use, not anything custom-built. **Risk to
  verify in Gate 3:** confirm Concept2's dev-server client registration accepts this
  redirect pattern before assuming the config flow will complete end-to-end.
- **CSRF/state protection (added on review):** provided by HA's
  `config_entry_oauth2_flow` base class (the `state` parameter is generated and
  validated automatically) — the integration does not implement or need any custom
  CSRF handling.
- **PKCE (considered on review, not adopted):** not added. This is a confidential
  client — the client secret is held server-side by HA, entered once via Application
  Credentials, never exposed to a browser/public client. PKCE exists to protect public
  clients that can't hold a secret; adding it here would be complexity without a
  matching threat. Revisit only if Concept2's API documentation mandates it.

#### 4.2.1 Current design: personal access token (D5, 2026-07-11)

- Plain `ConfigFlow` (not `AbstractOAuth2FlowHandler`), single password-masked
  field (`TextSelector`, `type: password`) for a Concept2 personal access token.
- User generates the token themselves at Concept2 profile → Edit Profile →
  Applications → Concept2 Logbook API - no client registration, no redirect URI,
  no Application Credentials platform involved at all.
- Validated by calling `GET /api/users/me` with the token as a Bearer header;
  `Concept2AuthError` (401) → `invalid_auth`, any other `Concept2ApiError`
  (including wrapped network/timeout failures, see below) → `cannot_connect`,
  anything unexpected → `unknown` (logged server-side via `_LOGGER.exception`,
  never shown raw to the user).
- Unique ID is the Concept2 user id returned by that call, exactly as before -
  reauth still matches entries correctly, `wrong_account` still guards against
  authenticating a second entry with a different Concept2 account's token.
- **Found while implementing, not anticipated in the brief:** `api.py` never
  actually caught raw `aiohttp` connection/timeout failures - they would have
  bubbled up unwrapped and landed in the config flow's generic `except
  Exception` → `unknown`, not `cannot_connect` as intended. Fixed by wrapping
  the request in `api.py` itself (`ClientError`/`TimeoutError` → `Concept2ApiError`),
  so `cannot_connect` means what it says regardless of caller.
- **Accepted tradeoff (see §2 C3 and SECURITY.md):** the token's scope is set by
  Concept2's own page at generation time and cannot be inspected, restricted, or
  verified by this integration's code - unlike the OAuth2 design above, which
  forced `user:read,results:read` explicitly on every token request. This
  integration still only ever issues GET requests (no write-capable method
  exists anywhere in `api.py`), so it cannot itself write to Concept2 regardless
  of the token's actual scope, but this is a narrower guarantee than the OAuth2
  design provided and is documented as such rather than presented as equivalent.
- Options flow (polling interval, F6) is unchanged - it never touched auth.

### 4.3 Data flow & API citizenship (C2)

- One coordinator per config entry; default poll every 10–15 minutes.
- Incremental sync via `updated_after` filter; full sync only on first setup.
- Respect pagination; cap page size per API docs.
- Handle deletes/updates of results gracefully via the local result store (§4.1.1) —
  results carry updated timestamps that drive upsert/remove into the store.
- **Back-off, corrected on review:** `DataUpdateCoordinator` does **not** provide
  exponential backoff out of the box — that was an inaccurate assumption. The
  coordinator's `_async_update_data` must implement its own consecutive-failure-counted
  exponential backoff on HTTP 429/5xx (honoring a `Retry-After` header when present)
  before raising `UpdateFailed`; this is custom code, not a framework freebie, and
  needs its own test coverage (T07).
- **Dev/production base URL (resolved at Gate 3 step 2, 2026-07-05 — supersedes
  the Gate 2 review note above):** `API_BASE_URL` is a single hardcoded constant in
  `const.py`, never a user- or config-flow-supplied value (required by A10 — no
  user-supplied URLs are ever fetched). Verified directly against Concept2's docs:
  "If you are only reading data from the Logbook, you can develop against
  production. If you are writing data to the Logbook, before using the live API,
  you must first develop against the development server." Since this integration
  requests no write scopes and `api.py` implements no write-capable methods,
  `API_BASE_URL` defaults to **production** (`https://log.concept2.com`), not the
  dev server — this is what Concept2's own terms require for a read-only client,
  not a relaxation of C2. `https://log-dev.concept2.com` stays defined as a
  separate constant, unused by default. See `CLAUDE.md` C2 for the recorded
  decision.
- **Scope must never be omitted from a token request (found verifying docs for
  step 2 — critical for C3):** Concept2's docs state that if `scope` is omitted
  from a `/oauth/access_token` call — including a **refresh** call — it silently
  defaults to `user:read,results:write`, i.e. write access. Home Assistant's
  default OAuth2 implementation does not resend `scope` on refresh automatically.
  Build step 3 (`application_credentials.py`) must override the token request to
  always explicitly attach `scope=user:read,results:read`, on both the initial
  exchange and every refresh, with a dedicated regression test — never rely on
  the default.

### 4.4 Repository structure (C1)

```
hacs-concept2-logbook/
├── custom_components/concept2_logbook/
│   ├── __init__.py            # setup, coordinator wiring
│   ├── manifest.json          # domain, version, deps, codeowners, iot_class: cloud_polling
│   ├── config_flow.py         # OAuth2 config + reauth + options flow
│   ├── application_credentials.py
│   ├── api.py                 # thin Concept2 API client
│   ├── coordinator.py
│   ├── sensor.py
│   ├── diagnostics.py         # redacted diagnostics export
│   ├── const.py
│   ├── strings.json
│   └── translations/en.json
├── hacs.json
├── README.md                  # install, self-service OAuth guide, security notes, attribution
├── SECURITY.md                # threat model summary, reporting, OWASP alignment
├── LICENSE (MIT)
├── CLAUDE.md                  # working agreement for Claude Code (see §7)
└── .github/workflows/         # hassfest + HACS validation + lint CI
```

### 4.5 Security design (C4 — OWASP alignment)

Mapped to OWASP Top 10 (2021) categories relevant to this integration:

| OWASP | Measure |
|-------|---------|
| A01 Broken Access Control | Read-only by design (no write-capable code path exists, regardless of token scope); no privileged operations; per-user personal access token (**updated 2026-07-11, D5** — was "per-user OAuth") |
| A02 Cryptographic Failures | TLS-only endpoints; tokens stored via HA's standard config-entry storage — **corrected on review:** this is the same protection level as every other HA core integration's tokens, not separate encryption added by this integration; at-rest protection ultimately depends on the host's file permissions/disk encryption, which is outside this integration's control and should be a one-line honest note in SECURITY.md rather than an implied guarantee. No secrets in repo, logs, or diagnostics. |
| A03 Injection | No dynamic query construction; all params URL-encoded via aiohttp; API responses validated before use |
| A04 Insecure Design | Least privilege, polling over inbound webhooks in v1, threat model in SECURITY.md |
| A05 Security Misconfiguration | Pinned dependency versions in manifest; CI validation (hassfest, HACS action) |
| A06 Vulnerable & Outdated Components (added on review — was missing from this table entirely, undermining the "OWASP mapping stays true" claim in C4) | Dependency versions pinned in `manifest.json`; GitHub Dependabot/security alerts enabled on the repo; minimum HA core version tracked and bumped deliberately, not left implicit |
| A07 Identification & Auth Failures | **Updated 2026-07-11, D5:** reauth flow triggered automatically on token revocation/expiry (401 → `ConfigEntryAuthFailed`); user-generated personal access token, not application-managed OAuth2 - see §4.2.1's scope-visibility tradeoff |
| A08 Software & Data Integrity | No runtime code download; dependency review. **No tagged release exists yet** (verified 2026-07-05 via `gh api`) - signed/tagged GitHub releases are the plan starting at v1.0.0 (Gate 5), not a current fact; corrected here after being stated as present tense |
| A09 Logging & Monitoring Failures | Structured logging with **no tokens/PII**; diagnostics export redacts identifiers using HA's built-in `homeassistant.components.diagnostics.async_redact_data` helper (added on review — reuses a reviewed HA core mechanism instead of ad hoc string matching, which is where redaction bugs usually creep in) |
| A10 SSRF | API base URLs are constants; no user-supplied URLs are fetched |

Audit support: every release tagged; CHANGELOG maintained; code comments explain
security-relevant decisions; SECURITY.md states AI-assisted origin (Claude Code) and
the human review requirement before every release.

**Review log:** Senior-HA-developer + security review performed 2026-07-05. Findings
and fixes are inlined above, marked "added/corrected on review" (local result store
for correct totals recompute; redirect URI and CSRF/PKCE notes; corrected backoff and
token-storage claims; resolved dev/prod base URL mechanism; added missing OWASP A06
row; diagnostics redaction now references HA's built-in helper). No changes were made
that touch C1–C4 themselves — all changes reinforce or correct the design's compliance
with them.

**Gate 2 exit criteria:** Stakeholder approves architecture, auth model
(per-user client credentials), repo layout, and security design. **Status: pending
your sign-off** — the review above is not itself an approval.

---

## 5. Build (Gate 3 — Development)

Executed in Claude Code, in this order:

1. Repo scaffold + CI (hassfest, HACS validation action, ruff lint) — fail fast on C1.
2. API client against Concept2 **dev server** + unit tests with mocked responses.
3. OAuth config flow + application credentials + reauth.
4. Coordinator + sensors + new-result event.
5. Options flow, diagnostics (redacted), translations.
6. README, SECURITY.md, CHANGELOG, screenshots.

**Gate 3 exit criteria:** CI green (lint + hassfest + HACS validation + unit tests);
all v1 functional requirements implemented; no TODOs in security-relevant code.

**Status: met, 2026-07-05.** All four CI checks pass on the current commit
(steps 1-5 complete; step 6 is docs-only, no code). One note on "HACS
validation green": while the repo was private (D4), 3-5 of 9 HACS checks
failed per push - verified via `curl` that this was GitHub's raw-content
endpoint returning 404 for private repos, not a real defect in our code
(confirmed by re-running all 9 historical validation runs after
going public 2026-07-05: every one dropped to exactly 1/9 failing -
`hacsjson` and `integration_manifest` now pass). The one remaining failure,
`brands`, was initially (and incorrectly) assumed to only apply to
default-store submissions, based on an AI-summarized doc read rather than
the actual validator source - **corrected 2026-07-05** after reading
`hacs/integration`'s `custom_components/hacs/validate/brands.py` directly:
the check runs unconditionally for any `integration`-category repository,
custom or default-store. Fixed properly instead of excused: added a local
`custom_components/concept2_logbook/brand/icon.png` (a plain placeholder,
not a designed logo - see README) which the validator accepts as one of its
two valid paths (the other being a domain listing in
home-assistant/brands). `ignore: brands` removed from `hacs.yml`
accordingly. F1-F6 all implemented and tested (§6.1); zero TODO/FIXME/XXX
in any source file (verified by grep across the full tree).

---

## 6. Test & Verification (Gate 4)

### 6.1 Automated test cases (pytest, mocked API)

| ID | Test case | Expected result |
|----|-----------|-----------------|
| T01 | Config flow happy path (mock OAuth) | Config entry created; coordinator starts |
| T02 | Config flow with denied consent | Flow aborts with clear user message; nothing stored |
| T03 | Token refresh on expiry | New token used transparently; no user interruption |
| T04 | Token revoked at Concept2 | Reauth flow triggered; entities marked unavailable, not crashed |
| T05 | First sync with N results | Sensors populated; no `concept2_new_result` event storm (initial sync suppressed) |
| T06 | Incremental sync detects 1 new result | Exactly one `concept2_new_result` event fired with correct payload |
| T07 | API returns 429 / 5xx | Coordinator backs off; entities keep last known state; recovery on next success |
| T08 | Malformed/unexpected API payload | Logged (redacted), gracefully skipped; no exception to HA core |
| T09 | Pagination across multiple pages | All results processed exactly once |
| T10 | Result updated/deleted upstream | Sensor state reflects change on next poll |
| T11 | Log output scan | No token, client secret, or e-mail address appears in any log line |
| T12 | Diagnostics export | Tokens and personal identifiers redacted |
| T13 | Options flow: polling interval below allowed minimum | Rejected with validation error |
| T14 | Unload/reload config entry | Clean teardown, no orphaned listeners |
| T15 | *(added on review)* Historical result edited/deleted upstream after being counted in a total | Lifetime/season/streak sensors recompute correctly from the local result store (§4.1.1), not just from the latest poll's delta |

### 6.2 Compliance verification

| ID | Check | Method |
|----|-------|--------|
| V01 | HACS requirements (C1) | HACS validation GitHub Action passes; manual checklist vs hacs.xyz docs |
| V02 | HA integration quality | `hassfest` action passes |
| V03 | Concept2 API terms (C2) | Manual review of docs vs implementation; dev-server testing before production request |
| V04 | OWASP mapping (C4) | Security review checklist in SECURITY.md walked through and signed off per release |

### 6.3 Manual acceptance tests (on stakeholder's live HA)

| ID | Scenario | Acceptance criterion |
|----|----------|----------------------|
| A01 | Install via HACS custom repository | Install + restart + config flow completes in < 10 min following README only |
| A02 | Authorize with real Concept2 account (dev, then prod after approval) | Consent screen shows exactly the two read permissions; entities appear |
| A03 | Row a workout, sync via ErgData | New result visible in HA within one polling cycle; event fired |
| A04 | Build Lovelace card from sensors | Metrics render correctly |
| A05 | TTS automation on `concept2_new_result` | Announcement plays with workout data |
| A06 | Revoke access from Concept2 Settings → Applications | HA prompts reauth; no errors flood the log |

**Gate 4 exit criteria:** All T/V/A cases pass; stakeholder acceptance recorded.

---

## 7. Release & Publication (Gate 5)

1. Tag v1.0.0 GitHub release with release notes and checksums.
2. Publish as HACS **custom repository**; README explains adding it.
3. Announce for community testing (HA Community forum thread).
4. Collect feedback → v1.x backlog (webhooks, more sensors, translations,
   HACS default-store submission, HA brands submission).

**Gate 5 exit criteria:** Public release live; installation verified from a clean HA instance.

---

## 8. Requirements for the Claude Code Collaboration

These become the project's `CLAUDE.md` working agreement:

1. **Constraints C1–C4 are law.** If a requested change would conflict with HACS
   rules, Concept2 API terms, or the security design, stop and flag it instead of
   implementing it.
2. **Stage-gate discipline.** Work proceeds in the gate order above; do not start a
   later stage's work while the current gate is open without explicit approval.
3. **Explore → Plan → Implement → Commit.** Present a plan (plan mode) before
   non-trivial changes; the stakeholder approves diffs in Ask-permissions mode.
4. **Security first.** Never write code that logs tokens/secrets/PII; never commit
   credentials; treat all API responses as untrusted input.
5. **Test with the code.** Every functional change ships with/updates its tests;
   CI must stay green.
6. **Small commits, clear messages,** conventional-commit style, so the audit trail
   (C4) is readable.
7. **Honest attribution.** Maintain the "built with Claude Code, human-reviewed"
   notice in README and SECURITY.md.

### Stakeholder responsibilities (you)

- Register the API client in the Concept2 developer portal (self-service) and manage
  the dev→production approval request with Concept2.
- Review and approve at each gate; run manual acceptance tests A01–A06 on your HA.
- Own the GitHub repository and releases.

---

## 9. Open Decisions (need your answer before Gate 1 closes)

| # | Decision | Options | Resolution |
|---|----------|---------|----------------|
| D1 | Final sensor list | **CLOSED 2026-07-05** — sensor set per §3.1 F3; PBs and per-split sensors deferred to v1.1 | — |
| D2 | Integration domain + display name | `concept2_logbook` vs `concept2`; display name/tagline | **CLOSED 2026-07-05** — domain: `concept2_logbook`; display name: "Concept2 Logbook"; tagline: "This integration connects Concept2 Logbook to Home Assistant over API using the official Concept2 API protocol." |
| D3 | License | MIT vs Apache-2.0 | **CLOSED 2026-07-05** — MIT |
| D4 | Repo visibility during build | Private until Gate 4, then public | **CLOSED 2026-07-05** — private through Gate 3's build steps; made public 2026-07-05 on stakeholder instruction, ahead of Gate 4's manual acceptance testing (A01-A06), specifically to unblock full HACS validation (see Gate 3 exit criteria note above). Gate 4 itself is not yet started. |
| D5 | Auth mechanism for v1.0 | OAuth2 Authorization Code (as originally built, §4.2) vs Concept2 personal access token | **CLOSED 2026-07-11** — personal access token (Edit Profile → Applications → Concept2 Logbook API), replacing the OAuth2 design built in Gate 3 step 3. Rationale: the stakeholder generated a token and confirmed the OAuth "API Key portal" client-registration flow is the app-developer path for multi-user distribution, not what an individual sees on their own profile - the personal token is what Concept2 actually intends for a single-user personal install like this one. Accepted tradeoff: token scope is set by Concept2's UI and not visible/restrictable by our code (§4.2, C3 amendment above) - this is weaker than the OAuth2 design's code-enforced explicit scope, and is documented as such rather than presented as equivalent. OAuth2 deferred to v1.x, not deleted from history. |

**Gate 1 exit criteria met 2026-07-05** — scope, sensor list (D1), domain/naming (D2), license (D3), and repo visibility (D4) all signed off. Gate 1 closed. D5 is a post-Gate-3 amendment (raised during Gate 4 prep, 2026-07-11), not a Gate 1 item — recorded here to keep all numbered decisions in one place.
