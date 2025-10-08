import logging

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SUNNY,
)

DOMAIN = "daikinskyport"
MANUFACTURER = "Daikin"

_LOGGER = logging.getLogger(__package__)

# Map Daikin weather icons to HA conditions (weather icons are always the same, *Cond change with language)
# Unknown entries are unverifed.  Taken from Weather Underground icon names
DAIKIN_WEATHER_ICON_TO_HASS = {
    "sunny": ATTR_CONDITION_SUNNY,  # Unknown
    "mostlysunny": ATTR_CONDITION_SUNNY,  # Unknown
    "partlysunny": ATTR_CONDITION_PARTLYCLOUDY,  # Unknown
    "partlycloudy": ATTR_CONDITION_PARTLYCLOUDY,
    "clear": ATTR_CONDITION_CLEAR_NIGHT,  # Unknown
    "mostlycloudy": ATTR_CONDITION_CLOUDY,
    "cloudy": ATTR_CONDITION_CLOUDY,  # Unknown
    "rain": ATTR_CONDITION_RAINY,
    "chancerain": ATTR_CONDITION_RAINY,
    "snow": ATTR_CONDITION_SNOWY,  # Unknown
    "chancesnow": ATTR_CONDITION_SNOWY,  # Unknown
    "chanceflurries": ATTR_CONDITION_SNOWY,  # Unknown
    "flurries": ATTR_CONDITION_SNOWY,  # Unknown
    "tstorms": ATTR_CONDITION_LIGHTNING,
    "chancetstorms": ATTR_CONDITION_LIGHTNING,
    "fog": ATTR_CONDITION_FOG,  # Unknown
    "hazy": "hazy",  # Unknown
    "sleet": "sleet",  # Unknown
    "chancesleet": "sleet",  # Unknown
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

COORDINATOR = "coordinator"
