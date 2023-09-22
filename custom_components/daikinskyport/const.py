import logging

_LOGGER = logging.getLogger(__package__)

DOMAIN = "daikinskyport"
MANUFACTURER = "Daikin"

from homeassistant.components.weather import (
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
)

DAIKIN_WEATHER_SYMBOL_TO_HASS = {
    "Sunny": ATTR_CONDITION_SUNNY,
    "Mostly Sunny": ATTR_CONDITION_PARTLYCLOUDY,
    "Partly Cloudy": ATTR_CONDITION_PARTLYCLOUDY,
    "Clear": ATTR_CONDITION_CLEAR_NIGHT,
    "Fair": ATTR_CONDITION_CLEAR_NIGHT,
    "Cloudy": ATTR_CONDITION_CLOUDY,
    "Rain": ATTR_CONDITION_RAINY,
    "Snow": ATTR_CONDITION_SNOWY, #Unknown
    "Snow and Rain": ATTR_CONDITION_SNOWY_RAINY, #Unknown
    "Hail": ATTR_CONDITION_HAIL, #Unknown
    "Thunderstorms": ATTR_CONDITION_LIGHTNING_RAINY,
    "AM Thunderstorms": ATTR_CONDITION_LIGHTNING_RAINY,
    "Thunderstorms Late": ATTR_CONDITION_LIGHTNING_RAINY,
    "Fog": ATTR_CONDITION_FOG, #Unknown
    "Hazy": "hazy", #Unknown
}

# The multiplier applied by the API to percentage values.
DAIKIN_PERCENT_MULTIPLIER = 2

# Possible hvac modes are auto (3), auxHeatOnly (4), cool (2), heat (1), off (0) '''
DAIKIN_HVAC_MODE_OFF = 0
DAIKIN_HVAC_MODE_HEAT = 1
DAIKIN_HVAC_MODE_COOL = 2
DAIKIN_HVAC_MODE_AUTO = 3
DAIKIN_HVAC_MODE_AUXHEAT = 4

CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCESS_TOKEN = "access_token"
