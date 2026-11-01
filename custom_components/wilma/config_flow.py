"""Config flow for Wilma integration."""

from __future__ import annotations

import logging
from typing import Any

import probatio
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from wilhelmina import AuthenticationError, WilmaClient, WilmaError

from .const import (
    CONF_PASSWORD,
    CONF_RECENT_THRESHOLD_HOURS,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_SERVER_URL,
    CONF_USERNAME,
    DEFAULT_RECENT_THRESHOLD_HOURS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_SERVER_URL): str,
        probatio.Required(CONF_USERNAME): str,
        probatio.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(data: dict[str, Any]) -> None:
    """Validate that the credentials work by logging in and listing messages.

    Uses a client with its own HTTP session: Wilma's session cookies must not end up in
    Home Assistant's shared session.
    """
    try:
        async with WilmaClient(data[CONF_SERVER_URL]) as client:
            await client.login(data[CONF_USERNAME], data[CONF_PASSWORD])
            await client.get_messages()
    except AuthenticationError as err:
        raise InvalidAuth from err
    except WilmaError as err:
        raise CannotConnect from err


class WilmaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wilma."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options for an existing entry."""
        return WilmaOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = {
                **user_input,
                CONF_SERVER_URL: user_input[CONF_SERVER_URL].strip().rstrip("/"),
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
            }
            await self.async_set_unique_id(
                f"{user_input[CONF_SERVER_URL].lower()}|{user_input[CONF_USERNAME].lower()}"
            )
            self._abort_if_unique_id_configured()

            try:
                await validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Wilma ({user_input[CONF_USERNAME]})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class WilmaOptionsFlow(OptionsFlow):
    """Polling interval and how long new items count as recent."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = probatio.Schema(
            {
                probatio.Required(
                    CONF_SCAN_INTERVAL_MINUTES,
                    default=options.get(
                        CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
                    ),
                ): probatio.All(probatio.Coerce(int), probatio.Range(min=5, max=360)),
                probatio.Required(
                    CONF_RECENT_THRESHOLD_HOURS,
                    default=options.get(
                        CONF_RECENT_THRESHOLD_HOURS, DEFAULT_RECENT_THRESHOLD_HOURS
                    ),
                ): probatio.All(probatio.Coerce(int), probatio.Range(min=1, max=168)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
