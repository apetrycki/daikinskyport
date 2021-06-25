"""Daikin Skyport integration."""
import logging
import os
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL,
)
from homeassistant.util import Throttle
from homeassistant.util.json import save_json

from .daikinskyport import DaikinSkyport
from .const import (
    _LOGGER,
    DOMAIN,
)

CONF_HOLD_TEMP = "hold_temp"

DAIKINSKYPORT_CONFIG_FILE = "daikinskyport.conf"

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)

NETWORK = None

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_EMAIL): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOLD_TEMP, default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

class DaikinSkyportData:
    """Get the latest data and update the states."""

    def __init__(self, config_file):
        """Init the Daikin Skyport data object."""

        self.daikinskyport = DaikinSkyport(config_file)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Get the latest data from daikinskyport."""
        self.daikinskyport.update()
        _LOGGER.debug("Daikin Skyport data updated successfully")


def setup(hass, config):
    """Set up the Daikin Skyport Thermostat.

    Will automatically load thermostat and sensor components to support
    devices discovered on the network.
    """

    # Create daikinskyport.conf if it doesn't exist
    if not os.path.isfile(hass.config.path(DAIKINSKYPORT_CONFIG_FILE)):
        jsonconfig = {"EMAIL": config[DOMAIN].get(CONF_EMAIL),
                      "PASSWORD": config[DOMAIN].get(CONF_PASSWORD)
                      }
        save_json(hass.config.path(DAIKINSKYPORT_CONFIG_FILE), jsonconfig)

    data = DaikinSkyportData(hass.config.path(DAIKINSKYPORT_CONFIG_FILE))
    hass.data[DOMAIN] = data
    
    hold_temp = config[DOMAIN].get(CONF_HOLD_TEMP)

    discovery.load_platform(hass, "climate", DOMAIN, {"hold_temp": hold_temp}, config)
    discovery.load_platform(hass, "sensor", DOMAIN, {}, config)
#    discovery.load_platform(hass, "binary_sensor", DOMAIN, {}, config)
    discovery.load_platform(hass, "weather", DOMAIN, {}, config)
    
    return True
