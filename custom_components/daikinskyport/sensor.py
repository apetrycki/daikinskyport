"""Support for Daikin Skyport sensors."""
from homeassistant.const import (
    PERCENTAGE,
    TEMP_CELSIUS,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    POWER_WATT
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.helpers.entity import Entity

from .const import (
    _LOGGER,
    DOMAIN,
)

DEVICE_CLASS_DEMAND = "demand"
DEVICE_CLASS_FREQ_PERCENT = "frequency in percent"
DEVICE_CLASS_ACTUAL_STATUS = "actual"

SENSOR_TYPES = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "native_unit_of_measurement": TEMP_CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer",
    },
    "humidity": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "native_unit_of_measurement": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:water-percent",
    },
    "CO2": {
        "device_class": SensorDeviceClass.CO2,
        "native_unit_of_measurement": CONCENTRATION_PARTS_PER_MILLION,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:periodic-table-co2",
    },
    "VOC": {
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        "native_unit_of_measurement": CONCENTRATION_PARTS_PER_BILLION,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:cloud",
    },
    "ozone": {
        "device_class": SensorDeviceClass.OZONE,
        "native_unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:cloud",
    },
    "particle": {
        "device_class": SensorDeviceClass.PM1,
        "native_unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:cloud",
    },
    "PM25": {
        "device_class": SensorDeviceClass.PM25,
        "native_unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:cloud",
    },
    "PM10": {
        "device_class": SensorDeviceClass.PM10,
        "native_unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:cloud",
    },
    "score": {
        "device_class": SensorDeviceClass.AQI,
        "native_unit_of_measurement": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:cloud",
    },
    "demand": {
        "device_class": DEVICE_CLASS_DEMAND,
        "native_unit_of_measurement": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:percent",
    },
    "power": {
        "device_class": SensorDeviceClass.POWER,
        "native_unit_of_measurement": POWER_WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:power-plug",
    },
    "frequency_percent": {
        "device_class": DEVICE_CLASS_FREQ_PERCENT,
        "native_unit_of_measurement": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:percent",
    },
    "actual_status": {
        "device_class": DEVICE_CLASS_ACTUAL_STATUS,
        "native_unit_of_measurement": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
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
            if sensor["type"] not in ("temperature", "humidity", "score",
                                      "ozone", "particle", "VOC", "demand",
                                      "power", "frequency_percent",
                                      "actual_status"):
                continue
                
            dev.append(DaikinSkyportSensor(data, sensor["name"], sensor["type"], index))

    add_entities(dev, True)


class DaikinSkyportSensor(SensorEntity):
    """Representation of a Daikin sensor."""

    def __init__(self, data, sensor_name, sensor_type, sensor_index):
        """Initialize the sensor."""
        self.data = data
        self._name = f"{sensor_name} {SENSOR_TYPES[sensor_type]['device_class']}"
        self._attr_unique_id = f"{data.daikinskyport.thermostats[sensor_index]['id']}-{self._name}"
        self._sensor_name = sensor_name
        self._type = sensor_type
        self._index = sensor_index
        self._state = None
        self._native_unit_of_measurement = SENSOR_TYPES[sensor_type]["native_unit_of_measurement"]

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
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._native_unit_of_measurement

    def update(self):
        """Get the latest state of the sensor."""
        self.data.update()
        for sensor in self.data.daikinskyport.get_sensors(self._index):
            if sensor["type"] == self._type and self._sensor_name == sensor["name"]:
                self._state = sensor["value"]
