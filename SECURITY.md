# Security

## Origin and review

**Built with Claude Code, human-reviewed, security-focused.**

[Claude Code](https://claude.com/claude-code) (Anthropic) wrote this integration under
the working agreement in `CLAUDE.md` and the design in
`concept2-ha-integration-design.md`. A person reviews each change before it is merged
and before each release. AI assistance does not replace this review.

## Threat model

- **Scope:** The integration reads only your own Concept2 Logbook results and the public
  challenge data. It sends requests only to the Concept2 API. It sends only `GET`
  requests, whatever scope the token has.
- **Credential:** The integration uses a personal access token. You create the token at
  Edit Profile → Applications → Concept2 Logbook API and paste it in the config flow.
  There is no client secret and no redirect URI.
- **Storage:** Home Assistant stores the token in the config entry. This is the same
  protection as for the credentials of other Home Assistant integrations. The integration
  does not encrypt the token again. The protection of the file on disk depends on the host.
- **Limit of the scope:** Concept2 sets the scope of the token when you create it. The
  integration cannot read, restrict or check this scope. An OAuth2 client would let the
  code request only `user:read,results:read`. The personal access token gives a weaker
  guarantee than this. The integration contains no method that writes to Concept2, so it
  cannot write even if the token allows it.
- **Revocation:** If you revoke the token at Concept2, the next poll gets a 401 response.
  Home Assistant then starts the reauthentication flow.
- **Logging:** The integration does not log or commit the token, e-mail addresses or other
  personal data. The diagnostics export redacts identifiers with the Home Assistant helper
  `async_redact_data`.

## OWASP Top 10 (2021)

| OWASP | Measure |
| --- | --- |
| A01 Broken Access Control | The code has no write path. There are no privileged operations. Each user has a personal token. |
| A02 Cryptographic Failures | All endpoints use TLS. The token is in the Home Assistant config entry. No secret is in the repository, the logs or the diagnostics. |
| A03 Injection | The code builds no query by hand. aiohttp encodes the parameters. The code validates each API response before it uses it. |
| A04 Insecure Design | The integration uses least privilege. It polls and does not accept inbound webhooks. |
| A05 Security Misconfiguration | Dependency versions are pinned. CI runs hassfest and the HACS action. GitHub secret scanning and push protection are on. |
| A06 Vulnerable and Outdated Components | Dependency versions are pinned. GitHub vulnerability alerts are on. The minimum Home Assistant version is set in `hacs.json`. |
| A07 Identification and Authentication Failures | A 401 response raises `ConfigEntryAuthFailed` and starts reauthentication. The user creates the token. Tested with a real revoked token. |
| A08 Software and Data Integrity | The integration does not download code at runtime. Each release is a tagged GitHub release. |
| A09 Logging and Monitoring Failures | The logs contain no token and no personal data. The diagnostics redact identifiers. |
| A10 Server-Side Request Forgery | The API base URLs are constants. The integration never fetches a URL from a user. |

The design document gives the reasons for each row.

## Report a vulnerability

Use the private vulnerability reporting of this repository: **Security → Report a
vulnerability**. Do not use a public issue. Do not include real tokens, secrets or
personal data in the report.
