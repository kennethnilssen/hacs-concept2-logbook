# Security

## Origin and review

This integration was built with [Claude Code](https://claude.com/claude-code)
(Anthropic) under a documented working agreement (`CLAUDE.md`) and design doc
(`concept2-ha-integration-design.md`), with human review at every stage-gate
before merge and before each release. AI assistance does not remove the human
review step — every release requires stakeholder sign-off (see the design
doc's Gate 4/5 exit criteria).

## Threat model summary

- **Scope:** this integration only reads the authenticated user's own Concept2
  Logbook results and public challenge data. It never writes to Concept2, never
  requests scopes beyond `user:read results:read`, and never talks to any host
  other than the Concept2 API.
- **Credentials:** each user registers their own OAuth2 client with Concept2 and
  enters it into Home Assistant's Application Credentials UI. No client secret
  is ever published in this repository. Access/refresh tokens are held only in
  Home Assistant's own config-entry storage — the same mechanism and protection
  level as every other HA core integration's tokens, not something separately
  encrypted by this integration. At-rest protection beyond that depends on the
  host's file permissions/disk encryption, which is outside this integration's
  control.
- **Revocation:** users can revoke access at any time from Concept2 Settings →
  Applications; Home Assistant will then trigger its standard reauth flow.
- **Logging:** tokens, client secrets, and e-mail addresses/other PII are never
  logged, printed, or committed. Diagnostics exports redact identifiers using
  Home Assistant's built-in redaction helper.

## OWASP Top 10 (2021) alignment

| OWASP | Measure |
|-------|---------|
| A01 Broken Access Control | Read-only scopes; no privileged operations; per-user OAuth |
| A02 Cryptographic Failures | TLS-only endpoints; tokens via HA's standard config-entry storage; no secrets in repo, logs, or diagnostics |
| A03 Injection | No dynamic query construction; all params URL-encoded via aiohttp; API responses validated before use |
| A04 Insecure Design | Least privilege; polling over inbound webhooks in v1 |
| A05 Security Misconfiguration | Pinned dependency versions in manifest; CI validation (hassfest, HACS action) |
| A06 Vulnerable & Outdated Components | Dependency versions pinned; GitHub Dependabot/security alerts enabled; minimum HA core version tracked deliberately |
| A07 Identification & Auth Failures | HA-managed OAuth2 with refresh rotation; reauth flow on revocation |
| A08 Software & Data Integrity | Signed/tagged GitHub releases; no runtime code download; dependency review |
| A09 Logging & Monitoring Failures | Structured logging with no tokens/PII; diagnostics redaction via HA's `async_redact_data` helper |
| A10 SSRF | API base URLs are hardcoded constants; no user-supplied URLs are ever fetched |

Full rationale for each row lives in `concept2-ha-integration-design.md` §4.5.

## Reporting a vulnerability

Please open a private GitHub security advisory on this repository (or, if
unavailable, open an issue asking for a private contact) rather than a public
issue. Do not include real tokens, secrets, or personal data in any report.
