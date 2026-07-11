"""Diagnostics support for Concept2 Logbook (T12).

Redacts anything that could identify the user or grant access - tokens,
the Concept2 account id/username, and free-text the user wrote themselves
(workout comments) - using Home Assistant's own `async_redact_data` helper
rather than ad hoc string matching (Gate 2 review, C4 / OWASP A09).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import Concept2Coordinator

TO_REDACT = {
    "access_token",
    "title",
    "unique_id",
    "username",
    "email",
    "profile_image",
    "comments",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: Concept2Coordinator = entry.runtime_data
    data = coordinator.data

    diagnostics = {
        "entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": coordinator.diagnostics_data,
        "data": {
            "last_result": data.last_result if data else None,
            "totals": data.totals if data else None,
            "current_challenge": data.current_challenge if data else None,
            "upcoming_challenge": data.upcoming_challenge if data else None,
        },
    }
    return async_redact_data(diagnostics, TO_REDACT)
