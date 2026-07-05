"""Tests for the Concept2 Logbook OAuth2 config flow (T01-T04)."""

from homeassistant import config_entries
from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.concept2_logbook.const import (
    API_BASE_URL,
    DOMAIN,
    OAUTH2_AUTHORIZE_URL,
    OAUTH2_TOKEN_URL,
)

CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"


async def _setup_credentials(hass):
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass, DOMAIN, ClientCredential(CLIENT_ID, CLIENT_SECRET), "test"
    )


async def _start_flow(hass):
    await _setup_credentials(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return result


async def test_full_flow_creates_entry(
    hass, hass_client_no_auth, aioclient_mock, current_request_with_host
):
    """T01: happy path - config entry created."""
    result = await _start_flow(hass)
    assert result["type"] == FlowResultType.EXTERNAL_STEP
    assert result["url"].startswith(OAUTH2_AUTHORIZE_URL)
    assert "scope=user:read,results:read" in result["url"]

    state = result["url"].split("state=")[1].split("&")[0]
    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200

    aioclient_mock.post(
        OAUTH2_TOKEN_URL,
        json={
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "token_type": "Bearer",
            "expires_in": 604800,
        },
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test-user"}},
    )

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-user"

    entry = result["result"]
    assert entry.unique_id == "1"
    assert entry.data["token"]["access_token"] == "mock-access-token"

    # The token request must always include our least-privilege scope,
    # never leaving it to the default implementation's behavior (C3).
    token_request = aioclient_mock.mock_calls[-2]
    assert token_request[2]["scope"] == "user:read,results:read"


async def test_flow_aborts_if_profile_fetch_fails(
    hass, hass_client_no_auth, aioclient_mock, current_request_with_host
):
    """T02 (adapted): if we can't confirm who authorized, abort cleanly."""
    result = await _start_flow(hass)
    state = result["url"].split("state=")[1].split("&")[0]

    client = await hass_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN_URL,
        json={
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "token_type": "Bearer",
            "expires_in": 604800,
        },
    )
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=401)

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"

    # Nothing should be stored if we aborted.
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_reauth_updates_existing_entry(
    hass, hass_client_no_auth, aioclient_mock, current_request_with_host
):
    """T04: reauth for the same account updates the entry in place."""
    await _setup_credentials(hass)

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "stale-token"},
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.EXTERNAL_STEP

    state = result["url"].split("state=")[1].split("&")[0]
    client = await hass_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN_URL,
        json={
            "access_token": "fresh-token",
            "refresh_token": "fresh-refresh-token",
            "token_type": "Bearer",
            "expires_in": 604800,
        },
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test-user"}},
    )

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["token"]["access_token"] == "fresh-token"


async def test_reauth_wrong_account_aborts(
    hass, hass_client_no_auth, aioclient_mock, current_request_with_host
):
    """T04 (extended): reauthenticating as a different Concept2 account is rejected."""
    await _setup_credentials(hass)

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="1",
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "stale-token"},
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    state = result["url"].split("state=")[1].split("&")[0]
    client = await hass_client_no_auth()
    await client.get(f"/auth/external/callback?code=abcd&state={state}")

    aioclient_mock.post(
        OAUTH2_TOKEN_URL,
        json={
            "access_token": "fresh-token",
            "refresh_token": "fresh-refresh-token",
            "token_type": "Bearer",
            "expires_in": 604800,
        },
    )
    # A *different* Concept2 user id than the entry being reauthenticated.
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 2, "username": "someone-else"}},
    )

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    # The original entry must be untouched.
    assert entry.data["token"]["access_token"] == "stale-token"
