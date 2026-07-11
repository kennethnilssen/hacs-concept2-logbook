"""Config flow for Concept2 Logbook.

Personal access token authentication (C3, D5 - 2026-07-11). Users generate
their own long-lived token at their Concept2 profile (Edit Profile ->
Applications -> Concept2 Logbook API) and paste it in - no OAuth client
registration, no redirect URI, no Application Credentials. One config entry
per Concept2 account, identified by the Concept2 user id so reauth can be
matched to the right entry and a second account can't silently overwrite
the first.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import Concept2ApiClient, Concept2ApiError, Concept2AuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_FULL_HISTORY_SYNC,
    CONF_SCAN_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

_TOKEN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class Concept2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Concept2 Logbook."""

    def __init__(self) -> None:
        super().__init__()
        self._pending_token: str | None = None
        self._pending_title: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> Concept2OptionsFlow:
        """Get the options flow for this handler (F6)."""
        return Concept2OptionsFlow()

    async def _async_validate_token(
        self, token: str
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Validate a token against the API. Returns (user, error_code)."""
        client = Concept2ApiClient(
            session=async_get_clientsession(self.hass), token=token
        )
        try:
            user = await client.async_get_user()
        except Concept2AuthError:
            return None, "invalid_auth"
        except Concept2ApiError:
            return None, "cannot_connect"
        except Exception:  # noqa: BLE001 - last-resort form error, logged for diagnosis
            _LOGGER.exception("Unexpected error validating Concept2 access token")
            return None, "unknown"
        return user, None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: paste a personal access token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_ACCESS_TOKEN]
            user, error = await self._async_validate_token(token)
            if error:
                errors["base"] = error
            else:
                user_id = str(user["id"])
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                self._pending_token = token
                self._pending_title = user.get("username") or user_id
                return await self.async_step_full_history_sync()

        return self.async_show_form(
            step_id="user", data_schema=_TOKEN_SCHEMA, errors=errors
        )

    async def async_step_full_history_sync(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask whether to do a full paginated history sync (F3).

        Unrelated to auth (D5) - kept unchanged from the OAuth2 design, per
        the non-goal of not touching sync behavior beyond auth plumbing.
        Opting in fetches the user's entire Concept2 history (paginated) on
        first setup, for accurate lifetime totals immediately. Opting out
        only fetches the most recent results; lifetime/season totals then
        start from whenever the integration was installed and grow from
        there - a documented v1 limitation, not a bug.
        """
        if user_input is None:
            return self.async_show_form(
                step_id="full_history_sync",
                data_schema=vol.Schema(
                    {vol.Required(CONF_FULL_HISTORY_SYNC, default=False): bool}
                ),
            )

        return self.async_create_entry(
            title=self._pending_title,
            data={
                CONF_ACCESS_TOKEN: self._pending_token,
                CONF_FULL_HISTORY_SYNC: user_input[CONF_FULL_HISTORY_SYNC],
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth triggered by token expiry/revocation (F5)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth: paste a fresh token for the same Concept2 account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_ACCESS_TOKEN]
            user, error = await self._async_validate_token(token)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(str(user["id"]))
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data={CONF_ACCESS_TOKEN: token}
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=_TOKEN_SCHEMA, errors=errors
        )


class Concept2OptionsFlow(OptionsFlow):
    """Options flow for Concept2 Logbook - polling interval only (F6)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the polling interval, enforcing a floor.

        The floor exists to be a good API citizen (C2) - Concept2's own docs
        currently say the API isn't rate limited, but that may change, and
        polling too aggressively is exactly the kind of abuse that would
        trigger it.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                scan_interval = vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_MINUTES)
                )(user_input[CONF_SCAN_INTERVAL_MINUTES])
            except vol.Invalid:
                errors["base"] = "scan_interval_too_low"
            else:
                return self.async_create_entry(
                    data={CONF_SCAN_INTERVAL_MINUTES: scan_interval}
                )

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_SCAN_INTERVAL_MINUTES, default=current): int}
            ),
            errors=errors,
            description_placeholders={"min_minutes": str(MIN_SCAN_INTERVAL_MINUTES)},
        )
