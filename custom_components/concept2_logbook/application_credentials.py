"""Application credentials platform for Concept2 Logbook.

Implements a custom OAuth2 implementation rather than relying on Home
Assistant's default `LocalOAuth2Implementation`, because Concept2 silently
defaults an omitted `scope` to include write access on every token request,
including refresh (verified against Concept2's docs during Gate 3 step 2).
The default implementation does not resend `scope` on refresh, so this
override guarantees the least-privilege scope (C3) is always sent
explicitly, on both the initial exchange and every refresh.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    API_KEY_PORTAL_URL,
    OAUTH2_AUTHORIZE_URL,
    OAUTH2_SCOPE_STRING,
    OAUTH2_TOKEN_URL,
)


class Concept2OAuth2Implementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Local OAuth2 implementation that always pins the least-privilege scope."""

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Add the required scope to the /oauth/authorize step."""
        return {"scope": OAUTH2_SCOPE_STRING}

    async def _token_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Attach scope to every token request, including refresh.

        See module docstring - this is the one thing that must never be
        left to the default implementation's behavior.
        """
        data["scope"] = OAUTH2_SCOPE_STRING
        return await super()._token_request(data)


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return the custom OAuth2 implementation for a registered credential."""
    return Concept2OAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        credential.client_secret,
        OAUTH2_AUTHORIZE_URL,
        OAUTH2_TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Return description placeholders shown in the Application Credentials UI."""
    return {
        "api_key_portal_url": API_KEY_PORTAL_URL,
        "redirect_url": config_entry_oauth2_flow.async_get_redirect_uri(hass),
    }
