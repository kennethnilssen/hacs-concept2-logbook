"""Tests for button.py - the "sync now" force-refresh button."""

from unittest.mock import AsyncMock

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.concept2_logbook.api import Concept2ApiClient
from custom_components.concept2_logbook.button import Concept2SyncButton
from custom_components.concept2_logbook.const import DOMAIN
from custom_components.concept2_logbook.coordinator import Concept2Coordinator


async def test_sync_button_press_requests_coordinator_refresh(hass):
    """Pressing the button must request a coordinator refresh directly -
    not a full integration reload - so it stays lightweight and correctly
    respects the coordinator's own rate-limit backoff.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    client = Concept2ApiClient(
        session=async_get_clientsession(hass), token="test-token"
    )
    coordinator = Concept2Coordinator(hass, entry, client)
    coordinator.async_request_refresh = AsyncMock()

    button = Concept2SyncButton(coordinator, entry)
    await button.async_press()

    coordinator.async_request_refresh.assert_awaited_once()
