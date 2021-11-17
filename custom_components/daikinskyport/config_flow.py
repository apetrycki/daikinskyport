"""Config flow for Daikin Skyport integration."""
from __future__ import annotations

import logging
from typing import Any

from requests.exceptions import ConnectionError

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL,CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .daikinskyport import request_tokens
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    try:
        auth = await request_tokens(data[CONF_EMAIL], data[CONF_PASSWORD])
    except ConnectionError:
        raise CannotConnect

    if auth is None:
        raise InvalidAuth

    return auth


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for name."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            info['email'] = user_input['email']
            info['password'] = user_input['password']
            return self.async_create_entry(title="Daikin Skyport", data=info)

        return self.async_show_form(
            step_id="email", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Cannot connect to Daikin Skyport. Try again later."""

class InvalidAuth(HomeAssistantError):
    """Error requesting token from Daikin Skyport. Please check your credentials."""

class TimeoutError(HomeAssistantError):
    """Timed out connecting to Daiking Skyport. Try again later."""
