from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_NAME
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN
import voluptuous as vol
from .daikinskyport import DaikinSkyport

class DaikinSkyportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    
    async def async_step_user(self, user_input):
        await self.async_set_unique_id(device_unique_id)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            try:
              async with timeout(10):
                daikinskyport = DaikinSkyport({
                  'EMAIL': user_input[CONF_EMAIL],
                  'PASSWORD': user_input[CONF_PASSWORD],
                })
                
            else:
                await self.async_set_unique_id(
                    daikinskyport.location_key, raise_on_progress=False #TBD
                )

                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
                  
        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema(
              {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_NAME, default="Daikin"): str,
              }
            )
        )  
      
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SchemaOptionsFlowHandler:
        """Options callback for AccuWeather."""
        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)
