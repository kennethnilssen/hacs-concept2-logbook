"""Thin async client for the Concept2 Logbook API.

Endpoints, parameters, and response shapes verified 2026-07-05 directly
against https://log.concept2.com/developers/documentation/ (constraint C2).
**Correction 2026-07-12:** live testing found the documentation doesn't
match reality on two points for the challenge endpoints - responses can
be mislabeled `Content-Type: text/html` even for JSON bodies, and "no
current/upcoming challenge" is a bare `{}`, not `{"data": []}`. Both are
handled defensively below rather than assumed away.

This client only implements GET requests - deliberately provides no method
capable of writing data, so there is no code path here that could
accidentally mutate a user's Concept2 account, regardless of which base URL
is configured. Authenticated requests use a personal access token supplied
by the caller (D5); this client never validates or restricts that token's
scope, since Concept2's API does not expose a way to inspect it (SECURITY.md).
"""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import (
    API_BASE_URL,
    API_VERSION_HEADER,
    CHALLENGES_CURRENT_PATH,
    CHALLENGES_UPCOMING_PATH,
    RESULTS_PATH,
    USER_PATH,
)


class Concept2ApiError(Exception):
    """Base error for any Concept2 API failure."""


class Concept2AuthError(Concept2ApiError):
    """Raised on HTTP 401 - token invalid/expired/revoked; caller should reauth."""


class Concept2RateLimitedError(Concept2ApiError):
    """Raised on HTTP 429."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class Concept2ServerError(Concept2ApiError):
    """Raised on HTTP 5xx - the coordinator backs off on this too (design doc §4.3)."""


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header value (seconds form only; ignore HTTP-date form)."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class Concept2ApiClient:
    """Thin wrapper around the Concept2 Logbook API."""

    def __init__(
        self,
        session: ClientSession,
        token: str | None = None,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Set up the client.

        `token` is only required for authenticated calls (results, user
        profile) - the public challenge endpoints work without one.
        """
        self._session = session
        self._token = token
        self._base_url = base_url

    async def _headers(self, *, authenticated: bool) -> dict[str, str]:
        headers = {"Accept": API_VERSION_HEADER}
        if authenticated:
            if self._token is None:
                raise Concept2ApiError(
                    "Authenticated request attempted without an access token"
                )
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _get(
        self,
        path: str,
        *,
        authenticated: bool,
        params: dict[str, Any] | None = None,
        allow_empty: bool = False,
    ) -> dict[str, Any]:
        """`allow_empty` accepts a bare `{}` (no `data` key) as a valid,
        no-content response - confirmed 2026-07-12 against a live account
        that Concept2's challenge endpoints return this when there is no
        current/upcoming challenge, rather than `{"data": []}`.
        """
        headers = await self._headers(authenticated=authenticated)
        try:
            async with self._session.get(
                f"{self._base_url}{path}", headers=headers, params=params
            ) as response:
                if response.status == 401:
                    raise Concept2AuthError(f"Concept2 API returned 401 for {path}")
                if response.status == 429:
                    retry_after = _parse_retry_after(
                        response.headers.get("Retry-After")
                    )
                    raise Concept2RateLimitedError(
                        f"Concept2 API returned 429 for {path}", retry_after=retry_after
                    )
                if response.status >= 500:
                    raise Concept2ServerError(
                        f"Concept2 API returned {response.status} for {path}"
                    )
                try:
                    response.raise_for_status()
                except ClientResponseError as err:
                    raise Concept2ApiError(
                        f"Concept2 API returned {response.status} for {path}"
                    ) from err
                # Concept2 sometimes mislabels JSON responses as text/html
                # (confirmed 2026-07-12, live, even with an explicit
                # `Accept: application/json`) - content_type=None skips
                # aiohttp's strict mimetype check; the shape check below
                # still validates the parsed body.
                payload = await response.json(content_type=None)
        except TimeoutError as err:
            raise Concept2ApiError(
                f"Timed out calling Concept2 API for {path}: {err}"
            ) from err
        except ClientError as err:
            raise Concept2ApiError(
                f"Network error calling Concept2 API for {path}: {err}"
            ) from err

        # Treat all API responses as untrusted input (C4 / OWASP A03):
        # validate the shape before handing it back to callers.
        if not isinstance(payload, dict):
            raise Concept2ApiError(f"Unexpected response shape from {path}")
        if "data" not in payload and not allow_empty:
            raise Concept2ApiError(f"Unexpected response shape from {path}")
        return payload

    async def async_get_user(self, user: str = "me") -> dict[str, Any]:
        """Fetch a user's profile. Requires `user:read`."""
        payload = await self._get(USER_PATH.format(user=user), authenticated=True)
        return payload["data"]

    async def async_get_results(
        self,
        user: str = "me",
        *,
        page: int | None = None,
        number: int | None = None,
        updated_after: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        type_: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one page of results. Requires `results:read`.

        Returns the full payload (`data` + `meta.pagination`) - walking
        pagination across pages is the coordinator's job (build step 4), not
        this client's.
        """
        params: dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if number is not None:
            params["number"] = number
        if updated_after is not None:
            params["updated_after"] = updated_after
        if from_ is not None:
            params["from"] = from_
        if to is not None:
            params["to"] = to
        if type_ is not None:
            params["type"] = type_
        return await self._get(
            RESULTS_PATH.format(user=user), authenticated=True, params=params
        )

    async def async_get_current_challenges(self) -> list[dict[str, Any]]:
        """Fetch current challenges. Public endpoint, no auth required.

        Returns an empty list when there is no current challenge - Concept2
        returns a bare `{}` for that case, not `{"data": []}`.
        """
        payload = await self._get(
            CHALLENGES_CURRENT_PATH, authenticated=False, allow_empty=True
        )
        return payload.get("data", [])

    async def async_get_upcoming_challenges(
        self, days: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch challenges upcoming within `days`. Public, no auth required.

        Returns an empty list when there is no upcoming challenge - see
        `async_get_current_challenges`.
        """
        payload = await self._get(
            CHALLENGES_UPCOMING_PATH.format(days=days),
            authenticated=False,
            allow_empty=True,
        )
        return payload.get("data", [])
