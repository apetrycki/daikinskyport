"""Support for Daikin Skyport sensors."""

from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    CONCENTRATION_PARTS_PER_MILLION,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    UnitOfPower,
    UnitOfVolumeFlowRate,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from . import DaikinSkyportData

from .const import (
    DOMAIN,
    COORDINATOR,
)

DEVICE_CLASS_DEMAND = "demand"
DEVICE_CLASS_FAULT_CODE = "Code"
DEVICE_CLASS_FREQ_PERCENT = "frequency in percent"
DEVICE_CLASS_ACTUAL_STATUS = "actual"
DEVICE_CLASS_AIR_FLOW = "airflow"

SENSOR_TYPES = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
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
        "native_unit_of_measurement": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:lightning-bolt",
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
    "airflow": {
        "device_class": DEVICE_CLASS_AIR_FLOW,
        "native_unit_of_measurement": UnitOfVolumeFlowRate.CUBIC_FEET_PER_MINUTE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:air-filter",
    },
    "fault_code": {
        "device_class": DEVICE_CLASS_FAULT_CODE,
        "native_unit_of_measurement": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:alert-circle",
    },
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add a Daikin Skyport Sensor entity from a config_entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DaikinSkyportData = data[COORDINATOR]

    for index in range(len(coordinator.daikinskyport.thermostats)):
        sensors = coordinator.daikinskyport.get_sensors(index)
        for sensor in sensors:
            if (
                sensor["type"]
                not in (
                    "temperature",
                    "humidity",
                    "score",
                    "ozone",
                    "particle",
                    "VOC",
                    "demand",
                    "power",
                    "frequency_percent",
                    "actual_status",
                    "airflow",
                    "fault_code",
                )
                or sensor["value"] == 127.5
                or sensor["value"] == 65535
            ):
                continue
            async_add_entities(
                [
                    DaikinSkyportSensor(
                        coordinator, sensor["name"], sensor["type"], index
                    )
                ],
                True,
            )


class DaikinSkyportSensor(SensorEntity):
    """Representation of a Daikin sensor."""

    def __init__(self, data, sensor_name, sensor_type, sensor_index):
        """Initialize the sensor."""
        self.data = data
        self._name = f"{sensor_name} {SENSOR_TYPES[sensor_type]['device_class']}"
        self._attr_unique_id = (
            f"{data.daikinskyport.thermostats[sensor_index]['id']}-{self._name}"
        )
        self._model = f"{data.daikinskyport.thermostats[sensor_index]['model']}"
        self._sensor_name = sensor_name
        self._type = sensor_type
        self._index = sensor_index
        self._state = None
        self._native_unit_of_measurement = SENSOR_TYPES[sensor_type][
            "native_unit_of_measurement"
        ]
        self._attr_state_class = SENSOR_TYPES[sensor_type]["state_class"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this Daikin Skyport thermostat."""
        return self.data.device_info

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

    async def async_update(self):
        """Get the latest state of the sensor."""
        await self.data._async_update_data()
        sensors = self.data.daikinskyport.get_sensors(self._index)
        for sensor in sensors:
            if sensor["type"] == self._type and self._sensor_name == sensor["name"]:
                # A fault code of 255 indicates that component (eg, the air
                # handler) is not present and therefore has no valid state. Experience
                # shows that 255 also indicates an issue with the component. In
                # either case, we do not return any value for the sensor.
                if sensor["type"] == "fault_code":
                    if sensor["value"] == 255:
                        continue
                    else:
                        self._state = sensor["value"]
                elif not sensor["value"] == 65535 and not sensor["value"] == 655350:
                    self._state = sensor["value"]
