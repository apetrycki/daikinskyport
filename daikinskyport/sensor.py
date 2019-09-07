"""Support for Daikin Skyport sensors."""
from homeassistant.components import daikinskyport
from homeassistant.const import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    TEMP_CELSIUS,
)
from homeassistant.helpers.entity import Entity

DAIKINSKYPORT_CONFIG_FILE = "daikinskyport.conf"

SENSOR_TYPES = {
    "temperature": ["Temperature", TEMP_CELSIUS],
    "humidity": ["Humidity", "%"],
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Daikin Skyport sensors."""
    if discovery_info is None:
        return
    data = daikinskyport.NETWORK
    dev = list()
    for index in range(len(data.daikinskyport.thermostats)):
        for sensor in data.daikinskyport.get_sensors(index):
            if sensor["type"] not in ("temperature", "humidity"):
                continue
                
            dev.append(DaikinSkyportSensor(sensor["name"], sensor["type"], index))

    add_entities(dev, True)


class DaikinSkyportSensor(Entity):
    """Representation of a Daikin sensor."""

    def __init__(self, sensor_name, sensor_type, sensor_index):
        """Initialize the sensor."""
        self._name = "{} {}".format(sensor_name, SENSOR_TYPES[sensor_type][0])
        self.sensor_name = sensor_name
        self.type = sensor_type
        self.index = sensor_index
        self._state = None
        self._unit_of_measurement = SENSOR_TYPES[sensor_type][1]
        #logger.error("name: %s, sensor_name: %s, type: %s, index: %s, unit: %s",
        #             self._name, self.sensor_name, self.type, self.index, self._unit_of_measurement)

    @property
    def name(self):
        """Return the name of the Daikin Skyport sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        if self.type in (DEVICE_CLASS_HUMIDITY, DEVICE_CLASS_TEMPERATURE):
            return self.type
        return None

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
        data = daikinskyport.NETWORK
        data.update()
        for sensor in data.daikinskyport.get_sensors(self.index):
            if sensor["type"] == self.type and self.sensor_name == sensor["name"]:
                self._state = sensor["value"]
