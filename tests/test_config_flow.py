"""Tests for the Concept2 Logbook personal-access-token config flow (D5)."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.concept2_logbook.const import API_BASE_URL, DOMAIN


async def _start_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_valid_token_creates_entry(hass, aioclient_mock):
    """T01: a valid token creates the entry, unique_id = Concept2 user id."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test-user"}},
    )

    result = await _start_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "valid-token"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "full_history_sync"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"full_history_sync": True}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test-user"

    entry = result["result"]
    assert entry.unique_id == "1"
    assert entry.data["access_token"] == "valid-token"
    assert entry.data["full_history_sync"] is True


async def test_invalid_token_shows_form_error(hass, aioclient_mock):
    """T02: a 401 during validation shows invalid_auth, stores nothing."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=401)

    result = await _start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "bad-token"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_auth"}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_same_account_twice_aborts_already_configured(hass, aioclient_mock):
    """T02b: adding the same Concept2 account a second time is rejected."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test-user"}},
    )
    existing = MockConfigEntry(
        domain=DOMAIN, unique_id="1", data={"access_token": "old-token"}
    )
    existing.add_to_hass(hass)

    result = await _start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "another-valid-token"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_network_error_shows_cannot_connect(hass, aioclient_mock):
    """T03: a network/server error during validation shows cannot_connect."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=500)

    result = await _start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "some-token"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_reauth_with_valid_token_for_same_account_updates_entry(
    hass, aioclient_mock
):
    """T04: reauth with a fresh token for the same account updates and reloads."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test-user"}},
    )
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="1", data={"access_token": "stale-token"}
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "fresh-token"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["access_token"] == "fresh-token"


async def test_reauth_with_different_account_aborts_wrong_account(hass, aioclient_mock):
    """Reauthenticating with a token for a different Concept2 account is rejected."""
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 2, "username": "someone-else"}},
    )
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="1", data={"access_token": "stale-token"}
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "someone-elses-token"}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert entry.data["access_token"] == "stale-token"


async def test_declining_history_sync_is_stored_as_false(hass, aioclient_mock):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test-user"}},
    )

    result = await _start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "valid-token"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"full_history_sync": False}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].data["full_history_sync"] is False


async def test_unexpected_error_during_validation_shows_unknown(hass, aioclient_mock):
    """A genuinely unexpected failure (not one of our known exception types)
    must still surface as a form error, not crash the flow.
    """
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", exc=ValueError("boom"))

    result = await _start_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "some-token"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_reauth_with_invalid_token_shows_form_error(hass, aioclient_mock):
    """An invalid token during reauth shows an error, doesn't crash or abort."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=401)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="1", data={"access_token": "stale-token"}
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"access_token": "still-bad-token"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data["access_token"] == "stale-token"
