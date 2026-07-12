"""Button platform for Concept2 Logbook - force an immediate sync."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Concept2Coordinator


class Concept2SyncButton(CoordinatorEntity[Concept2Coordinator], ButtonEntity):
    """Forces an immediate coordinator refresh.

    Lighter than reloading the integration (which tears down and rebuilds
    every entity) - just requests a fresh coordinator update, so it also
    correctly respects the coordinator's own rate-limit backoff rather than
    bypassing it.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "sync_now"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: Concept2Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_sync_now"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Concept2 Logbook",
            manufacturer="Concept2",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Concept2 Logbook sync button from a config entry."""
    coordinator: Concept2Coordinator = entry.runtime_data
    async_add_entities([Concept2SyncButton(coordinator, entry)])
