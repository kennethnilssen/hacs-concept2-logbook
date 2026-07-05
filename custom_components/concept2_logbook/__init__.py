"""The Concept2 Logbook integration.

Build status: scaffold only (Gate 3, step 1). Config flow, OAuth, the
coordinator, and sensors land in later build steps per the design doc §5 and
are intentionally not implemented yet.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Concept2 Logbook from a config entry.

    Placeholder until the OAuth config flow (step 3) and coordinator
    (step 4) exist — there is no config flow yet, so no entry can be
    created through normal use.
    """
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
