"""Binary sensor platform for Concept2 Logbook (F3 - "Workout done today")."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Concept2Coordinator


class Concept2WorkoutDoneTodayBinarySensor(
    CoordinatorEntity[Concept2Coordinator], BinarySensorEntity
):
    """Whether at least one workout has been logged today."""

    _attr_has_entity_name = True
    _attr_translation_key = "workout_done_today"

    def __init__(self, coordinator: Concept2Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_workout_done_today"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Concept2 Logbook",
            manufacturer="Concept2",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.totals.get("workout_done_today"))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Concept2 Logbook binary sensor from a config entry."""
    coordinator: Concept2Coordinator = entry.runtime_data
    async_add_entities([Concept2WorkoutDoneTodayBinarySensor(coordinator, entry)])
