"""Constants for the Concept2 Logbook integration.

API shapes below verified 2026-07-05 directly against
https://log.concept2.com/developers/documentation/ (constraint C2) - not
guessed.
"""

DOMAIN = "concept2_logbook"

# Least-privilege OAuth2 scopes (constraint C3, design doc §4.2). Concept2
# silently defaults an omitted scope to "user:read,results:write" (write
# access) on every token request, including refresh - so this must always be
# sent explicitly, never omitted. Do not widen without updating the design
# doc and re-running the security review.
OAUTH2_SCOPES = ["user:read", "results:read"]
OAUTH2_SCOPE_STRING = ",".join(OAUTH2_SCOPES)

DEFAULT_SCAN_INTERVAL_MINUTES = 15
MIN_SCAN_INTERVAL_MINUTES = 10
CONF_SCAN_INTERVAL_MINUTES = "scan_interval_minutes"

# This integration requests no write scopes and implements no write-capable
# methods, so per Concept2's own docs ("if you are only reading data... you
# can develop against production") production is the correct default, not a
# relaxation of C2. See CLAUDE.md C2 for the recorded decision. The dev
# server is a separate database (not a mirror of production) and is kept
# here only in case throwaway testing is ever wanted.
API_BASE_URL = "https://log.concept2.com"
API_BASE_URL_DEV = "https://log-dev.concept2.com"

OAUTH2_AUTHORIZE_PATH = "/oauth/authorize"
OAUTH2_TOKEN_PATH = "/oauth/access_token"
OAUTH2_AUTHORIZE_URL = f"{API_BASE_URL}{OAUTH2_AUTHORIZE_PATH}"
OAUTH2_TOKEN_URL = f"{API_BASE_URL}{OAUTH2_TOKEN_PATH}"

# Where a user registers their own OAuth client (verified 2026-07-05 - the
# docs link this exact path as "API Key portal"). Shown to the user in the
# Application Credentials dialog; never fetched by code (A10).
API_KEY_PORTAL_URL = f"{API_BASE_URL}/developers/keys"

USER_PATH = "/api/users/{user}"
RESULTS_PATH = "/api/users/{user}/results"
RESULT_PATH = "/api/users/{user}/results/{result_id}"
CHALLENGES_CURRENT_PATH = "/api/challenges/current"
CHALLENGES_UPCOMING_PATH = "/api/challenges/upcoming/{days}"

# Sent as the Accept header on every request per Concept2's versioning
# recommendation, to avoid being silently moved to a future API version.
API_VERSION_HEADER = "application/vnd.c2logbook.v1+json"

DEFAULT_RESULTS_PAGE_SIZE = 50
MAX_RESULTS_PAGE_SIZE = 250

# Whether the user opted into a full paginated history sync on first setup
# (F3) - captured as a config-flow step in build step 4, since it depends on
# the coordinator that didn't exist yet in step 3.
CONF_FULL_HISTORY_SYNC = "full_history_sync"

EVENT_NEW_RESULT = "concept2_new_result"

STORAGE_VERSION = 1

# Concept2's polling API has no "deleted ids" feed (only its webhook does,
# out of scope for v1) - detecting a delete means periodically re-fetching
# and diffing against the local store (§4.1.1). Bounded to the date range
# already known locally, so this never silently expands scope beyond
# whatever the user already opted into via CONF_FULL_HISTORY_SYNC.
FULL_RESYNC_INTERVAL_HOURS = 24

# Defensive cap on pages walked in one sync - total_pages from the API is
# authoritative; this only guards against a pathological/buggy response
# (C4 - treat all API responses as untrusted input).
MAX_FULL_SYNC_PAGES = 100

# Concept2 season: May 1 - April 30 (CLAUDE.md technical conventions).
SEASON_START_MONTH = 5
SEASON_START_DAY = 1

# A deliberately simple v1 definition of "round-number lifetime milestone"
# for the concept2_new_result event's extras (F4) - every 100km crossed.
LIFETIME_MILESTONE_METERS = 100_000
