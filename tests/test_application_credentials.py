"""Tests for the custom OAuth2 implementation (application_credentials.py).

Concept2 silently defaults an omitted `scope` to include write access on
every token request, including refresh (verified against Concept2's docs,
Gate 3 step 2). These tests exist specifically because Home Assistant's
default LocalOAuth2Implementation does NOT resend `scope` on refresh - if
someone ever "simplified" this back to the default, these would catch it.
"""

from homeassistant.components.application_credentials import ClientCredential

from custom_components.concept2_logbook.application_credentials import (
    Concept2OAuth2Implementation,
    async_get_auth_implementation,
    async_get_description_placeholders,
)
from custom_components.concept2_logbook.const import (
    API_KEY_PORTAL_URL,
    DOMAIN,
    OAUTH2_AUTHORIZE_URL,
    OAUTH2_SCOPE_STRING,
    OAUTH2_TOKEN_URL,
)


async def test_extra_authorize_data_includes_scope(hass):
    implementation = Concept2OAuth2Implementation(
        hass,
        DOMAIN,
        "client-id",
        "client-secret",
        OAUTH2_AUTHORIZE_URL,
        OAUTH2_TOKEN_URL,
    )
    assert implementation.extra_authorize_data == {"scope": OAUTH2_SCOPE_STRING}


async def test_refresh_token_request_includes_scope(hass, aioclient_mock):
    """T03: refreshing an expired token must still send scope explicitly."""
    implementation = Concept2OAuth2Implementation(
        hass,
        DOMAIN,
        "client-id",
        "client-secret",
        OAUTH2_AUTHORIZE_URL,
        OAUTH2_TOKEN_URL,
    )
    aioclient_mock.post(
        OAUTH2_TOKEN_URL,
        json={
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 604800,
        },
    )

    await implementation.async_refresh_token(
        {"refresh_token": "old-refresh-token", "access_token": "old-access-token"}
    )

    refresh_request = aioclient_mock.mock_calls[-1]
    assert refresh_request[2]["grant_type"] == "refresh_token"
    assert refresh_request[2]["refresh_token"] == "old-refresh-token"
    assert refresh_request[2]["scope"] == OAUTH2_SCOPE_STRING


async def test_async_get_auth_implementation_returns_custom_class(hass):
    credential = ClientCredential("client-id", "client-secret")
    implementation = await async_get_auth_implementation(hass, DOMAIN, credential)

    assert isinstance(implementation, Concept2OAuth2Implementation)
    assert implementation.client_id == "client-id"
    assert implementation.client_secret == "client-secret"
    assert implementation.authorize_url == OAUTH2_AUTHORIZE_URL
    assert implementation.token_url == OAUTH2_TOKEN_URL


async def test_description_placeholders(hass, current_request_with_host):
    placeholders = await async_get_description_placeholders(hass)
    assert placeholders["api_key_portal_url"] == API_KEY_PORTAL_URL
    assert "redirect_url" in placeholders
