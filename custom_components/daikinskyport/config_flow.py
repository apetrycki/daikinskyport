from __future__ import annotations

from requests.exceptions import RequestException
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)

from .const import CONF_ACCESS_TOKEN, CONF_REFRESH_TOKEN, DOMAIN
from .daikinskyport import DaikinSkyport

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default="Daikin"): str,
    }
)
OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}


class DaikinSkyportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1

    async def async_step_user(self, user_input=None):
        self._abort_if_unique_id_configured()
        if user_input is not None:
            daikinskyport = DaikinSkyport(
                config={
                    "EMAIL": user_input[CONF_EMAIL],
                    "PASSWORD": user_input[CONF_PASSWORD],
                }
            )
            result = await self.hass.async_add_executor_job(
                daikinskyport.request_tokens
            )
            if result is None:
                raise HomeAssistantError(
                    "Authentication failure. Verify username and password are correct."
                )

            await self.async_set_unique_id(
                daikinskyport.user_email, raise_on_progress=False
            )

            user_input[CONF_ACCESS_TOKEN] = daikinskyport.access_token
            user_input[CONF_REFRESH_TOKEN] = daikinskyport.refresh_token

            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_NAME, default="Daikin"): str,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SchemaOptionsFlowHandler:
        """Options callback for DaikinSkyport."""
        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)
