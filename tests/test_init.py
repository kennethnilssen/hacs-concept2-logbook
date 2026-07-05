"""Scaffold-level tests (Gate 3 step 1).

Real coverage for the API client, OAuth config flow, coordinator, and sensors
lands alongside those build steps. A full `hass.config_entries.async_setup()`
round-trip isn't tested yet because that requires a real `config_flow.py`
(build step 3) — Home Assistant's config entry manager needs it to be
importable even for a manually-constructed MockConfigEntry. Until then, this
only proves the setup/unload stubs behave as documented when called directly.
"""

from unittest.mock import MagicMock

from custom_components.concept2_logbook import async_setup_entry, async_unload_entry


async def test_async_setup_entry_returns_true(hass):
    """The scaffold's setup stub returns True and does nothing else yet."""
    entry = MagicMock()
    assert await async_setup_entry(hass, entry) is True


async def test_async_unload_entry_returns_true(hass):
    """The scaffold's unload stub returns True and does nothing else yet."""
    entry = MagicMock()
    assert await async_unload_entry(hass, entry) is True
