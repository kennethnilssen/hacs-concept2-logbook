"""Constants for the Concept2 Logbook integration."""

DOMAIN = "concept2_logbook"

# Least-privilege OAuth2 scopes (constraint C3, design doc §4.2). Do not widen
# without updating the design doc and re-running the security review.
OAUTH2_SCOPES = ["user:read", "results:read"]

DEFAULT_SCAN_INTERVAL_MINUTES = 15
MIN_SCAN_INTERVAL_MINUTES = 10

# NOTE: API base URL / OAuth endpoint constants are intentionally NOT defined
# here yet. They land in api.py during build step 2, once verified against
# the real Concept2 API documentation (constraint C2) rather than guessed.
