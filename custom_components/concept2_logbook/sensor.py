"""Sensor platform for Concept2 Logbook (F3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import Concept2Coordinator, Concept2Data


@dataclass(frozen=True, kw_only=True)
class Concept2SensorEntityDescription(SensorEntityDescription):
    """Describes a Concept2 sensor whose state is derived from coordinator data."""

    value_fn: Callable[[Concept2Data], Any]
    attrs_fn: Callable[[Concept2Data], dict[str, Any]] | None = None


def _last_result(data: Concept2Data) -> dict[str, Any] | None:
    return data.last_result


def _last_result_value(key: str) -> Callable[[Concept2Data], Any]:
    def _get(data: Concept2Data) -> Any:
        result = _last_result(data)
        return None if result is None else result.get(key)

    return _get


def _last_result_time_seconds(data: Concept2Data) -> float | None:
    result = _last_result(data)
    if result is None or result.get("time") is None:
        return None
    return result["time"] / 10  # API time is tenths of a second (CLAUDE.md)


def _last_result_pace_seconds(data: Concept2Data) -> float | None:
    """Pace per 500m (or 1000m for BikeErg) in seconds."""
    result = _last_result(data)
    if not result or not result.get("distance") or not result.get("time"):
        return None
    seconds = result["time"] / 10
    unit_distance = 1000 if result.get("type") == "bike" else 500
    return round(seconds / (result["distance"] / unit_distance), 1)


def _last_result_heart_rate(key: str) -> Callable[[Concept2Data], Any]:
    def _get(data: Concept2Data) -> Any:
        result = _last_result(data)
        if result is None:
            return None
        return (result.get("heart_rate") or {}).get(key)

    return _get


def _last_result_date(data: Concept2Data) -> datetime | None:
    """Concept2's date has no explicit timezone - assumed to be HA's local zone."""
    result = _last_result(data)
    if result is None or not result.get("date"):
        return None
    naive = datetime.strptime(result["date"], "%Y-%m-%d %H:%M:%S")
    return dt_util.as_utc(naive.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))


def _last_result_distance_attrs(data: Concept2Data) -> dict[str, Any]:
    result = _last_result(data)
    if result is None:
        return {}
    return {
        "machine_type": result.get("type"),
        "workout_type": result.get("workout_type"),
        "source": result.get("source"),
        "verified": result.get("verified"),
        "ranked": result.get("ranked"),
        "comments": result.get("comments"),
    }


def _last_result_stroke_rate_attrs(data: Concept2Data) -> dict[str, Any]:
    result = _last_result(data)
    if result is None:
        return {}
    return {"stroke_count": result.get("stroke_count")}


def _last_result_heart_rate_attrs(data: Concept2Data) -> dict[str, Any]:
    result = _last_result(data)
    if result is None:
        return {}
    heart_rate = result.get("heart_rate") or {}
    return {
        "min": heart_rate.get("min"),
        "max": heart_rate.get("max"),
        "ending": heart_rate.get("ending"),
    }


def _last_synced_at(data: Concept2Data) -> datetime | None:
    """Our own sync timestamp - generated with dt_util.utcnow(), so unlike
    workout dates it's already known-UTC, no local-timezone guess needed.
    """
    if not data.last_synced_at:
        return None
    naive = datetime.strptime(data.last_synced_at, "%Y-%m-%d %H:%M:%S")
    return naive.replace(tzinfo=dt_util.UTC)


def _total(key: str) -> Callable[[Concept2Data], Any]:
    def _get(data: Concept2Data) -> Any:
        return data.totals.get(key)

    return _get


def _challenge_value(which: str) -> Callable[[Concept2Data], Any]:
    def _get(data: Concept2Data) -> Any:
        challenge = (
            data.current_challenge if which == "current" else data.upcoming_challenge
        )
        return None if challenge is None else challenge.get("name")

    return _get


def _challenge_attrs(which: str) -> Callable[[Concept2Data], dict[str, Any]]:
    def _get(data: Concept2Data) -> dict[str, Any]:
        challenge = (
            data.current_challenge if which == "current" else data.upcoming_challenge
        )
        if challenge is None:
            return {}
        return {
            "end_date": challenge.get("end_date"),
            "description": challenge.get("description"),
        }

    return _get


SENSOR_DESCRIPTIONS: tuple[Concept2SensorEntityDescription, ...] = (
    Concept2SensorEntityDescription(
        key="last_workout_distance",
        translation_key="last_workout_distance",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_last_result_value("distance"),
        attrs_fn=_last_result_distance_attrs,
    ),
    Concept2SensorEntityDescription(
        key="last_workout_time",
        translation_key="last_workout_time",
        native_unit_of_measurement="s",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_last_result_time_seconds,
    ),
    Concept2SensorEntityDescription(
        key="last_workout_average_pace",
        translation_key="last_workout_average_pace",
        native_unit_of_measurement="s",
        value_fn=_last_result_pace_seconds,
    ),
    Concept2SensorEntityDescription(
        key="last_workout_stroke_rate",
        translation_key="last_workout_stroke_rate",
        native_unit_of_measurement="spm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_last_result_value("stroke_rate"),
        attrs_fn=_last_result_stroke_rate_attrs,
    ),
    Concept2SensorEntityDescription(
        key="last_workout_calories",
        translation_key="last_workout_calories",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_last_result_value("calories_total"),
    ),
    Concept2SensorEntityDescription(
        key="last_workout_average_heart_rate",
        translation_key="last_workout_average_heart_rate",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_last_result_heart_rate("average"),
        attrs_fn=_last_result_heart_rate_attrs,
    ),
    Concept2SensorEntityDescription(
        key="last_workout_drag_factor",
        translation_key="last_workout_drag_factor",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_last_result_value("drag_factor"),
    ),
    Concept2SensorEntityDescription(
        key="last_workout_date",
        translation_key="last_workout_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_result_date,
    ),
    Concept2SensorEntityDescription(
        key="meters_today",
        translation_key="meters_today",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("meters_today"),
    ),
    Concept2SensorEntityDescription(
        key="meters_this_week",
        translation_key="meters_this_week",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("meters_this_week"),
    ),
    Concept2SensorEntityDescription(
        key="meters_this_month",
        translation_key="meters_this_month",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("meters_this_month"),
    ),
    Concept2SensorEntityDescription(
        key="meters_this_season",
        translation_key="meters_this_season",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("meters_this_season"),
    ),
    Concept2SensorEntityDescription(
        key="meters_lifetime",
        translation_key="meters_lifetime",
        native_unit_of_measurement=UnitOfLength.METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("meters_lifetime"),
    ),
    Concept2SensorEntityDescription(
        key="workouts_this_week",
        translation_key="workouts_this_week",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("workouts_this_week"),
    ),
    Concept2SensorEntityDescription(
        key="workouts_this_month",
        translation_key="workouts_this_month",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("workouts_this_month"),
    ),
    Concept2SensorEntityDescription(
        key="calories_this_month",
        translation_key="calories_this_month",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("calories_this_month"),
    ),
    Concept2SensorEntityDescription(
        key="workout_streak",
        translation_key="workout_streak",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_total("workout_streak"),
    ),
    Concept2SensorEntityDescription(
        key="current_challenge",
        translation_key="current_challenge",
        value_fn=_challenge_value("current"),
        attrs_fn=_challenge_attrs("current"),
    ),
    Concept2SensorEntityDescription(
        key="upcoming_challenge",
        translation_key="upcoming_challenge",
        value_fn=_challenge_value("upcoming"),
        attrs_fn=_challenge_attrs("upcoming"),
    ),
    Concept2SensorEntityDescription(
        key="last_synced",
        translation_key="last_synced",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_last_synced_at,
    ),
)


class Concept2Sensor(CoordinatorEntity[Concept2Coordinator], SensorEntity):
    """A single Concept2 Logbook sensor, driven by a shared coordinator."""

    _attr_has_entity_name = True
    entity_description: Concept2SensorEntityDescription

    def __init__(
        self,
        coordinator: Concept2Coordinator,
        entry: ConfigEntry,
        description: Concept2SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Concept2 Logbook",
            manufacturer="Concept2",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Concept2 Logbook sensors from a config entry."""
    coordinator: Concept2Coordinator = entry.runtime_data
    async_add_entities(
        Concept2Sensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )
