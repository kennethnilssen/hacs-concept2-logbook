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


def _client(hass, token: str | None = "test-access-token") -> Concept2ApiClient:
    return Concept2ApiClient(session=async_get_clientsession(hass), token=token)


async def test_get_user_returns_data_and_sends_bearer_token(hass, aioclient_mock):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        json={"data": {"id": 1, "username": "test"}},
    )
    client = _client(hass, token="secret-token")

    result = await client.async_get_user()

    assert result == {"id": 1, "username": "test"}
    sent_headers = aioclient_mock.mock_calls[0][3]
    assert sent_headers["Authorization"] == "Bearer secret-token"


async def test_get_results_sends_expected_query_params(hass, aioclient_mock):
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me/results",
        json={"data": [], "meta": {"pagination": {"total": 0}}},
    )
    client = _client(hass)

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
    # No token at all - public endpoints must not require one.
    client = _client(hass, token=None)

    result = await client.async_get_current_challenges()

    assert result == [{"id": 1, "name": "Test Challenge"}]
    sent_headers = aioclient_mock.mock_calls[0][3]
    assert "Authorization" not in sent_headers


async def test_get_current_challenges_empty_response_returns_empty_list(
    hass, aioclient_mock
):
    """Concept2 returns a bare `{}`, not `{"data": []}`, when there is no
    current challenge - confirmed 2026-07-12 against a live account. This
    must not raise "unexpected response shape".
    """
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/current", json={})
    client = _client(hass, token=None)

    result = await client.async_get_current_challenges()

    assert result == []


async def test_get_upcoming_challenges_empty_response_returns_empty_list(
    hass, aioclient_mock
):
    aioclient_mock.get(f"{API_BASE_URL}/api/challenges/upcoming/30", json={})
    client = _client(hass, token=None)

    result = await client.async_get_upcoming_challenges()

    assert result == []


async def test_get_current_challenges_tolerates_mislabeled_content_type(
    hass, aioclient_mock
):
    """Concept2 sometimes serves JSON with `Content-Type: text/html`
    (confirmed 2026-07-12, live, even with an explicit
    `Accept: application/json`). aiohttp's default strict mimetype check
    would otherwise reject this with a ContentTypeError.
    """
    aioclient_mock.get(
        f"{API_BASE_URL}/api/challenges/current",
        json={"data": [{"id": 1, "name": "Test Challenge"}]},
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    client = _client(hass, token=None)

    result = await client.async_get_current_challenges()

    assert result == [{"id": 1, "name": "Test Challenge"}]


async def test_get_user_empty_response_still_raises(hass, aioclient_mock):
    """Unlike the challenge endpoints, /api/users/me must always have `data` -
    `allow_empty` is opt-in per endpoint, not a global weakening of the
    untrusted-input shape check (C4 / OWASP A03).
    """
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", json={})
    client = _client(hass)

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()


async def test_401_raises_auth_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=401)
    client = _client(hass)

    with pytest.raises(Concept2AuthError):
        await client.async_get_user()


async def test_429_raises_rate_limited_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me/results", status=429)
    client = _client(hass)

    with pytest.raises(Concept2RateLimitedError):
        await client.async_get_results()


async def test_server_error_raises_generic_api_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=500)
    client = _client(hass)

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()


async def test_malformed_response_raises_api_error(hass, aioclient_mock):
    """A response missing the expected "data" key must not be trusted (C4/A03)."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", json={"unexpected": "shape"})
    client = _client(hass)

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()


async def test_authenticated_call_without_token_raises(hass, aioclient_mock):
    client = _client(hass, token=None)

    with pytest.raises(Concept2ApiError):
        await client.async_get_user()


async def test_token_never_appears_in_exception_messages(hass, aioclient_mock):
    """T11: even on failure, the token must never leak into an error message."""
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", status=401)
    client = _client(hass, token="super-secret-token-value")

    with pytest.raises(Concept2AuthError) as exc_info:
        await client.async_get_user()

    assert "super-secret-token-value" not in str(exc_info.value)


async def test_connection_error_raises_api_error(hass, aioclient_mock):
    """Network/timeout failures must be wrapped, not leaked raw (used by
    config_flow to distinguish cannot_connect from a genuinely unexpected
    error).
    """
    import errno

    import aiohttp
    from aiohttp.client_reqrep import ConnectionKey

    connection_key = ConnectionKey(
        host="log.concept2.com",
        port=443,
        is_ssl=True,
        ssl=None,
        proxy=None,
        proxy_auth=None,
        proxy_headers_hash=None,
    )
    aioclient_mock.get(
        f"{API_BASE_URL}/api/users/me",
        exc=aiohttp.ClientConnectorError(
            connection_key=connection_key,
            os_error=OSError(errno.ECONNREFUSED, "Connection refused"),
        ),
    )
    client = _client(hass, token="super-secret-token-value")

    with pytest.raises(Concept2ApiError) as exc_info:
        await client.async_get_user()

    # The underlying aiohttp error must be visible - a bare "Network error"
    # with no detail is undiagnosable from logs alone (this is the gap that
    # made a real production failure impossible to root-cause from the UI).
    assert "Connection refused" in str(exc_info.value)
    assert "super-secret-token-value" not in str(exc_info.value)


async def test_timeout_raises_api_error(hass, aioclient_mock):
    aioclient_mock.get(f"{API_BASE_URL}/api/users/me", exc=TimeoutError())
    client = _client(hass, token="super-secret-token-value")

    with pytest.raises(Concept2ApiError) as exc_info:
        await client.async_get_user()

    assert "super-secret-token-value" not in str(exc_info.value)
