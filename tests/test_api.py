"""Unit tests for the Concept2 API client.

All requests are mocked (`aioclient_mock`) - no live calls to Concept2 ever
run in automated tests, per the design doc's test plan and constraint C2.
"""

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.concept2_logbook.api import (
    Concept2ApiClient,
    Concept2ApiError,
    Concept2AuthError,
    Concept2RateLimitedError,
)
from custom_components.concept2_logbook.const import API_BASE_URL


class FakeOAuthSession:
    """Stand-in for config_entry_oauth2_flow.OAuth2Session in tests.

    The real OAuth2Session lands in build step 3; this only needs to satisfy
    the two things api.py actually calls on it.
    """

    def __init__(self, access_token: str = "test-access-token") -> None:
        self.token = {"access_token": access_token}
        self.ensure_valid_calls = 0

    async def async_ensure_token_valid(self) -> None:
        self.ensure_valid_calls += 1


def _client(hass, oauth_session=None) -> Concept2ApiClient:
    return Concept2ApiClient(
        session=async_get_clientsession(hass), oauth_session=oauth_session
    )


async def test_get_user_returns_data_and_sends_bearer_token(hass, aioclient_mock):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test"}},
    )
    oauth_session = FakeOAuthSession(access_token="secret-token")
    client = _client(hass, oauth_session)

    result = await client.async_get_user()

    assert result == {"id": 1, "username": "test"}
    assert oauth_session.ensure_valid_calls == 1
    sent_headers = aioclient_mock.mock_calls[0][3]
    assert sent_headers["Authorization"] == "Bearer secret-token"


async def test_get_results_sends_expected_query_params(hass, aioclient_mock):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={"data": [], "meta": {"pagination": {"total": 0}}},
    )
    client = _client(hass, FakeOAuthSession())

    payload = await client.async_get_results(
        updated_after="2026-07-01 00:00:00",
        page=2,
        number=100,
        from_="2026-01-01",
        to="2026-07-01",
        type_="rower",
    )

    assert payload["meta"]["pagination"]["total"] == 0
    sent_params = aioclient_mock.mock_calls[0][1].query
    assert sent_params["updated_after"] == "2026-07-01 00:00:00"
    assert sent_params["to"] == "2026-07-01"
    assert sent_params["type"] == "rower"
    assert sent_params["page"] == "2"
    assert sent_params["number"] == "100"


async def test_get_current_challenges_sends_no_authorization_header(
    hass, aioclient_mock
):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/challenges/current",
        json={"data": [{"id": 1, "name": "Test Challenge"}]},
    )
    # No oauth_session at all - public endpoints must not require one.
    client = _client(hass, oauth_session=None)

    result = await client.async_get_current_challenges()

    assert result == [{"id": 1, "name": "Test Challenge"}]
    sent_headers = aioclient_mock.mock_calls[0][3]
    assert "Authorization" not in sent_headers


async def test_401_raises_auth_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=401)
    client = _client(hass, FakeOAuthSession())

    with pytest.raises(Concept2AuthError):
        await client.async_get_user()


async def test_429_raises_rate_limited_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me/results", status=429)
    client = _client(hass, FakeOAuthSession())

    with pytest.raises(Concept2RateLimitedError):
        await client.async_get_results()


async def test_server_error_raises_generic_api_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=500)
    client = _client(hass, FakeOAuthSession())

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()


async def test_malformed_response_raises_api_error(hass, aioclient_mock):
    """A response missing the expected "data" key must not be trusted (C4/A03)."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", json={"unexpected": "shape"})
    client = _client(hass, FakeOAuthSession())

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()


async def test_authenticated_call_without_oauth_session_raises(hass, aioclient_mock):
    client = _client(hass, oauth_session=None)

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()
