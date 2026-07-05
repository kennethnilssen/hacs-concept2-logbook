"""Thin async client for the Concept2 Logbook API.

Endpoints, parameters, and response shapes verified 2026-07-05 directly
against https://log.concept2.com/developers/documentation/ (constraint C2).

This client only implements GET requests. v1 requests no write scopes
(`user:read results:read` only, C3) and deliberately provides no method
capable of writing data - there is no code path here that could accidentally
mutate a user's Concept2 account, regardless of which base URL is
configured.
"""

from __future__ import annotations

from typing import Any

from aiohttp import ClientResponseError, ClientSession
from homeassistant.helpers import config_entry_oauth2_flow

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


class Concept2ApiClient:
    """Thin wrapper around the Concept2 Logbook API."""

    def __init__(
        self,
        session: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session | None = None,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Set up the client.

        `oauth_session` is only required for authenticated calls (results,
        user profile) - the public challenge endpoints work without one.
        """
        self._session = session
        self._oauth_session = oauth_session
        self._base_url = base_url

    async def _headers(self, *, authenticated: bool) -> dict[str, str]:
        headers = {"Accept": API_VERSION_HEADER}
        if authenticated:
            if self._oauth_session is None:
                raise Concept2ApiError(
                    "Authenticated request attempted without an OAuth2 session"
                )
            await self._oauth_session.async_ensure_token_valid()
            access_token = self._oauth_session.token["access_token"]
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    async def _get(
        self,
        path: str,
        *,
        authenticated: bool,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = await self._headers(authenticated=authenticated)
        async with self._session.get(
            f"{self._base_url}{path}", headers=headers, params=params
        ) as response:
            if response.status == 401:
                raise Concept2AuthError(f"Concept2 API returned 401 for {path}")
            if response.status == 429:
                raise Concept2RateLimitedError(f"Concept2 API returned 429 for {path}")
            try:
                response.raise_for_status()
            except ClientResponseError as err:
                raise Concept2ApiError(
                    f"Concept2 API returned {response.status} for {path}"
                ) from err
            payload = await response.json()

        # Treat all API responses as untrusted input (C4 / OWASP A03):
        # validate the shape before handing it back to callers.
        if not isinstance(payload, dict) or "data" not in payload:
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
        """Fetch current challenges. Public endpoint, no auth required."""
        payload = await self._get(CHALLENGES_CURRENT_PATH, authenticated=False)
        return payload["data"]

    async def async_get_upcoming_challenges(
        self, days: int = 30
    ) -> list[dict[str, Any]]:
        """Fetch challenges upcoming within `days`. Public, no auth required."""
        payload = await self._get(
            CHALLENGES_UPCOMING_PATH.format(days=days), authenticated=False
        )
        return payload["data"]
