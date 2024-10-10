"""Daikin Skyport switch"""
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import (
    _LOGGER,
    COORDINATOR,
    DOMAIN,
    DAIKIN_HVAC_MODE_AUXHEAT,
    DAIKIN_HVAC_MODE_HEAT
)
from . import DaikinSkyportData

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add a Daikin Skyport Switch entity from a config_entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DaikinSkyportData = data[COORDINATOR]

    for index in range(len(coordinator.daikinskyport.thermostats)):
        thermostat = coordinator.daikinskyport.get_thermostat(index)
        async_add_entities([DaikinSkyportAuxHeat(coordinator, thermostat["name"], index)], True)

class DaikinSkyportAuxHeat(SwitchEntity):
    """Representation of Daikin Skyport aux_heat data."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, data, name, index):
        """Initialize the Daikin Skyport aux_heat platform."""
        self.data = data
        self._name = f"{name} Aux Heat"
        self._attr_unique_id = f"{data.daikinskyport.thermostats[index]['id']}-{self._name}"
        self._index = index
        self.aux_on = False

    @property
    def name(self) -> str:
        """Name of the switch."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Status of the switch."""
        return self.aux_on

    def turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        send_command = self.data.daikinskyport.set_hvac_mode(self._index, DAIKIN_HVAC_MODE_AUXHEAT)
        if send_command:
            self.aux_on = True
            self.schedule_update_ha_state()
        else:
            raise HomeAssistantError(f"Error {send_command}: Failed to turn on {self._name}")

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        if self.data.daikinskyport.get_thermostat(self._index)['mode'] == DAIKIN_HVAC_MODE_AUXHEAT:
            self.data.daikinskyport.set_hvac_mode(self._index, DAIKIN_HVAC_MODE_HEAT)
        self.aux_on = False
        self.schedule_update_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return self.data.device_info

    async def async_update(self) -> None:
        """Get the latest state of the switch."""
        _LOGGER.debug("Updating switch entity")
        await self.data._async_update_data()
        thermostat = self.data.daikinskyport.get_thermostat(self._index)
        if thermostat['mode'] == DAIKIN_HVAC_MODE_AUXHEAT:
            self.aux_on = True
        else:
            self.aux_on = False
