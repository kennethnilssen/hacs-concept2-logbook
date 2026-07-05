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
