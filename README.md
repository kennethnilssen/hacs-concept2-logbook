# Concept2 Logbook — Home Assistant Integration

This integration connects Concept2 Logbook to Home Assistant over API using the
official Concept2 API protocol.

> **Status: under construction (Gate 3 build in progress).** Not yet installable
> or usable — see `concept2-ha-integration-design.md` for the full design and
> build plan. This notice will be replaced with real install/setup instructions
> once the config flow and sensors exist.

## Scope

Reads your own logged Concept2 Logbook results (RowErg/SkiErg/BikeErg) and
exposes them as Home Assistant sensors and an event for automations. Read-only;
does not connect to live PM5 telemetry (see the design doc for the full
scope/out-of-scope list).

## Security

- OAuth2 Authorization Code flow via Home Assistant's Application Credentials —
  you authorize with your own Concept2 account and can revoke access at any
  time from Concept2 Settings → Applications.
- Requests only `user:read results:read` scopes — nothing else.
- No credentials are ever stored in this repository or logged.
- See `SECURITY.md` for the full threat model and OWASP alignment.

## Attribution

Built with [Claude Code](https://claude.com/claude-code), human-reviewed,
security-focused. See `CLAUDE.md` for the working agreement this project was
built under.

## License

MIT — see `LICENSE`.
