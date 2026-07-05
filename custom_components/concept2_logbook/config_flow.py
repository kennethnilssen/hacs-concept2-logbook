"""Config flow for Concept2 Logbook.

OAuth2 Authorization Code flow via Home Assistant's Application Credentials
platform (C3) - one config entry per Concept2 account, identified by the
Concept2 user id so reauth can be matched to the right entry and a second
account can't silently overwrite the first.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Concept2ApiClient, Concept2ApiError
from .const import DOMAIN, OAUTH2_SCOPE_STRING

_LOGGER = logging.getLogger(__name__)


class _StaticTokenSession:
    """Expose just enough of OAuth2Session to reuse Concept2ApiClient.

    Used once, right after the token exchange, to fetch the user's profile
    for the entry's unique_id/title - before a config entry (and therefore a
    real OAuth2Session) exists yet.
    """

    def __init__(self, token: dict[str, Any]) -> None:
        self.token = token

    async def async_ensure_token_valid(self) -> None:
        """No-op - the token was just issued, so it's already valid."""


class Concept2ConfigFlow(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow for Concept2 Logbook."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return the logger for this flow."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Belt-and-suspenders: also request the scope at the flow level.

        The authoritative fix lives on Concept2OAuth2Implementation in
        application_credentials.py; this just mirrors it so the requested
        scope is never dependent on only one code path.
        """
        return {"scope": OAUTH2_SCOPE_STRING}

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth triggered by token expiry/revocation (F5)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth, then fall through to the normal OAuth2 flow."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create (or update, on reauth) the config entry from a fresh token."""
        client = Concept2ApiClient(
            session=async_get_clientsession(self.hass),
            oauth_session=_StaticTokenSession(data["token"]),
        )
        try:
            user = await client.async_get_user()
        except Concept2ApiError:
            return self.async_abort(reason="cannot_connect")

        user_id = str(user["id"])
        await self.async_set_unique_id(user_id)

        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data=data
            )

        self._abort_if_unique_id_configured()
        title = user.get("username") or user_id
        return self.async_create_entry(title=title, data=data)
