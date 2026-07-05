"""The Concept2 Logbook integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Concept2ApiClient
from .coordinator import Concept2Coordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type Concept2ConfigEntry = ConfigEntry[Concept2Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: Concept2ConfigEntry) -> bool:
    """Set up Concept2 Logbook from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    client = Concept2ApiClient(
        session=async_get_clientsession(hass), oauth_session=oauth_session
    )

    coordinator = Concept2Coordinator(hass, entry, client)
    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Concept2ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
