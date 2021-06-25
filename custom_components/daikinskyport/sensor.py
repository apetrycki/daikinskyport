"""Support for Daikin Skyport sensors."""
from homeassistant.const import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    TEMP_CELSIUS,
)
from homeassistant.helpers.entity import Entity

from .const import (
    _LOGGER,
    DOMAIN,
)
DAIKINSKYPORT_CONFIG_FILE = "daikinskyport.conf"

DEVICE_CLASS_PM2_5 = "PM2.5"
DEVICE_CLASS_PM10 = "PM10"
DEVICE_CLASS_CARBON_DIOXIDE = "CO2"
DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS = "VOC"
DEVICE_CLASS_OZONE = "ozone"
DEVICE_CLASS_SCORE = "score"

SENSOR_TYPES = {
    "temperature": {
        "device_class": DEVICE_CLASS_TEMPERATURE,
        "unit_of_measurement": TEMP_CELSIUS,
        "icon": "mdi:thermometer",
    },
    "humidity": {
        "device_class": DEVICE_CLASS_HUMIDITY,
        "unit_of_measurement": "%",
        "icon": "mdi:water-percent",
    },
    "CO2": {
        "device_class": DEVICE_CLASS_CARBON_DIOXIDE,
        "unit_of_measurement": "ppm",
        "icon": "mdi:periodic-table-co2",
    },
    "VOC": {
        "device_class": DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS,
        "unit_of_measurement": "ppb",
        "icon": "mdi:cloud",
    },
    "ozone": {
        "device_class": DEVICE_CLASS_OZONE,
        "unit_of_measurement": "ppb",
        "icon": "mdi:cloud",
    },
    "particle": {
        "device_class": DEVICE_CLASS_PM2_5,
        "unit_of_measurement": "µg/m3",
        "icon": "mdi:cloud",
    },
    "PM25": {
        "device_class": DEVICE_CLASS_PM2_5,
        "unit_of_measurement": "µg/m3",
        "icon": "mdi:cloud",
    },
    "PM10": {
        "device_class": DEVICE_CLASS_PM10,
        "unit_of_measurement": "µg/m3",
        "icon": "mdi:cloud",
    },
    "score": {
        "device_class": DEVICE_CLASS_SCORE,
        "unit_of_measurement": "%",
        "icon": "mdi:percent",
    },
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Daikin Skyport sensors."""
    if discovery_info is None:
        return
    data = hass.data[DOMAIN]
    dev = list()
    for index in range(len(data.daikinskyport.thermostats)):
        for sensor in data.daikinskyport.get_sensors(index):
            if sensor["type"] not in ("temperature", "humidity", "score", "ozone", "particle", "VOC"):
                continue
                
            dev.append(DaikinSkyportSensor(data, sensor["name"], sensor["type"], index))

    add_entities(dev, True)


class DaikinSkyportSensor(Entity):
    """Representation of a Daikin sensor."""

    def __init__(self, data, sensor_name, sensor_type, sensor_index):
        """Initialize the sensor."""
        self.data = data
        self._name = "{} {}".format(sensor_name, SENSOR_TYPES[sensor_type]["device_class"])
        self._sensor_name = sensor_name
        self._type = sensor_type
        self._index = sensor_index
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[sensor_type]["unit_of_measurement"]

    @property
    def name(self):
        """Return the name of the Daikin Skyport sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if self._type in SENSOR_TYPES:
            return self._type
        return None

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return SENSOR_TYPES[self._type]["icon"]

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    def update(self):
        """Get the latest state of the sensor."""
        self.data.update()
        for sensor in self.data.daikinskyport.get_sensors(self._index):
            if sensor["type"] == self._type and self._sensor_name == sensor["name"]:
                self._state = sensor["value"]
