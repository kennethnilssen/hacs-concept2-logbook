"""Tests for the polling-interval options flow (F6, T13)."""

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.concept2_logbook.const import (
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)


def _entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_shows_current_value(hass):
    entry = _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert (
        result["data_schema"]({})[CONF_SCAN_INTERVAL_MINUTES]
        == DEFAULT_SCAN_INTERVAL_MINUTES
    )


async def test_options_flow_accepts_valid_interval(hass):
    entry = _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_SCAN_INTERVAL_MINUTES: 30}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL_MINUTES] == 30


async def test_options_flow_rejects_interval_below_minimum(hass):
    """T13: polling interval below the allowed minimum is rejected."""
    entry = _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL_MINUTES: MIN_SCAN_INTERVAL_MINUTES - 1},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "scan_interval_too_low"}
