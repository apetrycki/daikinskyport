"""Support for Daikin Skyport Thermostats."""
import collections
import logging
from typing import Optional

import voluptuous as vol

from homeassistant.components import daikinskyport
from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_HIGH,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_AUX_HEAT,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    SUPPORT_FAN_MODE,
    PRESET_AWAY,
    FAN_AUTO,
    FAN_ON,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    SUPPORT_PRESET_MODE,
    PRESET_NONE,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_DRY,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ON,
    ATTR_TEMPERATURE,
    TEMP_FAHRENHEIT,
    TEMP_CELSIUS,
    CONF_PASSWORD,
    CONF_EMAIL,
)
import homeassistant.helpers.config_validation as cv

_CONFIGURING = {}
_LOGGER = logging.getLogger(__name__)

ATTR_FAN_MIN_ON_TIME = "fan_min_on_time"
ATTR_RESUME_ALL = "resume_all"

DEFAULT_RESUME_ALL = False
PRESET_TEMPERATURE = "temp"
PRESET_VACATION = "vacation"
PRESET_HOLD_NEXT_TRANSITION = "next_transition"
PRESET_HOLD_INDEFINITE = "indefinite"
AWAY_MODE = "awayMode"
PRESET_HOME = "home"
PRESET_SLEEP = "sleep"

# Order matters, because for reverse mapping we don't want to map HEAT to AUX
DAIKIN_HVAC_TO_HASS = collections.OrderedDict(
    [
        (1, HVAC_MODE_HEAT),
        (2, HVAC_MODE_COOL),
        (3, HVAC_MODE_AUTO),
        (0, HVAC_MODE_OFF),
        (4, HVAC_MODE_HEAT),
    ]
)

DAIKIN_FAN_TO_HASS = collections.OrderedDict(
    [
        (0, FAN_AUTO),
        (1, FAN_ON),
        (2, FAN_AUTO),
    ]
)

DAIKIN_HVAC_ACTION_TO_HASS = {
    # Map to None if we do not know how to represent.
    1: CURRENT_HVAC_COOL,
    3: CURRENT_HVAC_HEAT,
    4: CURRENT_HVAC_FAN,
    2: CURRENT_HVAC_DRY,
    5: CURRENT_HVAC_IDLE,
}

"""
PRESET_TO_ECOBEE_HOLD = {
    PRESET_HOLD_NEXT_TRANSITION: "nextTransition",
    PRESET_HOLD_INDEFINITE: "indefinite",
}

SERVICE_SET_FAN_MIN_ON_TIME = "ecobee_set_fan_min_on_time"
SERVICE_RESUME_PROGRAM = "ecobee_resume_program"
"""

SET_FAN_MIN_ON_TIME_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Required(ATTR_FAN_MIN_ON_TIME): vol.Coerce(int),
    }
)

RESUME_PROGRAM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_RESUME_ALL, default=DEFAULT_RESUME_ALL): cv.boolean,
    }
)

SUPPORT_FLAGS = (
    SUPPORT_TARGET_TEMPERATURE
    #    | SUPPORT_PRESET_MODE
    | SUPPORT_AUX_HEAT
    | SUPPORT_TARGET_TEMPERATURE_RANGE
    | SUPPORT_FAN_MODE
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Daikin Skyport Thermostat Platform."""
    if discovery_info is None:
        return
    data = daikinskyport.NETWORK
    hold_temp = discovery_info["hold_temp"]
    _LOGGER.info(
        "Loading daikinskyport thermostat component with hold_temp set to %s", hold_temp
        )
    
    devices = [
        Thermostat(data, index, hold_temp)
        for index in range(len(data.daikinskyport.thermostats))
    ]
    add_entities(devices)

    '''
    def fan_min_on_time_set_service(service):
        """Set the minimum fan on time on the target thermostats."""
        entity_id = service.data.get(ATTR_ENTITY_ID)
        fan_min_on_time = service.data[ATTR_FAN_MIN_ON_TIME]

        if entity_id:
            target_thermostats = [
                device for device in devices if device.entity_id in entity_id
            ]
        else:
            target_thermostats = devices

        for thermostat in target_thermostats:
            thermostat.set_fan_min_on_time(str(fan_min_on_time))

            thermostat.schedule_update_ha_state(True)
    '''
    '''
    def resume_program_set_service(service):
        """Resume the program on the target thermostats."""
        entity_id = service.data.get(ATTR_ENTITY_ID)
        resume_all = service.data.get(ATTR_RESUME_ALL)

        if entity_id:
            target_thermostats = [
                device for device in devices if device.entity_id in entity_id
            ]
        else:
            target_thermostats = devices

        for thermostat in target_thermostats:
            thermostat.resume_program(resume_all)

            thermostat.schedule_update_ha_state(True)
    '''
    '''
    hass.services.register(
        DOMAIN,
        SERVICE_SET_FAN_MIN_ON_TIME,
        fan_min_on_time_set_service,
        schema=SET_FAN_MIN_ON_TIME_SCHEMA,
    )
    '''
    '''
    hass.services.register(
        DOMAIN,
        SERVICE_RESUME_PROGRAM,
        resume_program_set_service,
        schema=RESUME_PROGRAM_SCHEMA,
    )
    '''

class Thermostat(ClimateDevice):
    """A thermostat class for Daikin Skyport Thermostats."""

    def __init__(self, data, thermostat_index, hold_temp):
        """Initialize the thermostat."""
        self.data = data
        self.thermostat_index = thermostat_index
        self.thermostat = self.data.daikinskyport.get_thermostat(self.thermostat_index)
        self._name = self.thermostat["name"]
        self.hold_temp = hold_temp
        self.vacation = None

        self._operation_list = []
        if self.thermostat["ctSystemCapEmergencyHeat"] or (self.thermostat["ctOutdoorNoofHeatStates"] > 0):
            self._operation_list.append(HVAC_MODE_HEAT)
        if (self.thermostat["ctOutdoorNoofCoolStages"] > 0):
            self._operation_list.append(HVAC_MODE_COOL)
        if len(self._operation_list) == 2:
            self._operation_list.insert(0, HVAC_MODE_AUTO)
        self._operation_list.append(HVAC_MODE_OFF)
        '''
        self._preset_modes = {
            comfort["climateRef"]: comfort["name"]
            for comfort in self.thermostat["program"]["climates"]
        }
        '''
        self._fan_modes = [FAN_AUTO, FAN_ON]
        self.update_without_throttle = False

    def update(self):
        """Get the latest state from the thermostat."""
        if self.update_without_throttle:
            self.data.update(no_throttle=True)
            self.update_without_throttle = False
        else:
            self.data.update()

        self.thermostat = self.data.daikinskyport.get_thermostat(self.thermostat_index)

    @property
    def available(self):
        """Return if device is available."""
        return True #TBD: Need to determine how to tell if the thermostat is available or not

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the Ecobee Thermostat."""
        return self.thermostat["name"]

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.thermostat["tempIndoor"]

    @property
    def target_temperature_low(self):
        """Return the lower bound temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_AUTO:
            return self.thermostat["hspActive"]
        return None

    @property
    def target_temperature_high(self):
        """Return the upper bound temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_AUTO:
            return self.thermostat["cspActive"]
        return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_AUTO:
            return None
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self.thermostat["hspActive"]
        if self.hvac_mode == HVAC_MODE_COOL:
            return self.thermostat["cspActive"]
        return None

    @property
    def fan(self):
        """Return the current fan status."""
        if self.thermostat["ctAHFanCurrentDemandStatus"] > 0:
            return STATE_ON
        return HVAC_MODE_OFF

    @property
    def fan_mode(self):
        """Return the fan setting."""
        return DAIKIN_FAN_TO_HASS[self.thermostat["fanCirculate"]] #0=off, 1=always on, 2=schedule

    @property
    def fan_modes(self):
        """Return the available fan modes."""
        return self._fan_modes

    '''
    @property
    def preset_mode(self):
        """Return current preset mode."""
        events = self.thermostat["events"]
        for event in events:
            if not event["running"]:
                continue

            if event["type"] == "hold":
                if event["holdClimateRef"] in self._preset_modes:
                    return self._preset_modes[event["holdClimateRef"]]

                # Any hold not based on a climate is a temp hold
                return PRESET_TEMPERATURE
            if event["type"].startswith("auto"):
                # All auto modes are treated as holds
                return event["type"][4:].lower()
            if event["type"] == "vacation":
                self.vacation = event["name"]
                return PRESET_VACATION

        return self._preset_modes[self.thermostat["program"]["currentClimateRef"]]
    '''

    @property
    def hvac_mode(self):
        """Return current operation."""
        return DAIKIN_HVAC_TO_HASS[self.thermostat["mode"]]

    @property
    def hvac_modes(self):
        """Return the operation modes list."""
        return self._operation_list

    @property
    def current_humidity(self) -> Optional[int]:
        """Return the current humidity."""
        return self.thermostat["humIndoor"]

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        return DAIKIN_HVAC_ACTION_TO_HASS[self.thermostat["equipmentStatus"]]

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        status = self.thermostat["equipmentStatus"]
        return {
            "fan": self.fan,
            "schedule_mode": self.thermostat["schedEnabled"],
            "fan_cfm": self.thermostat["ctAHCurrentIndoorAirflow"],
            "fan_demand": self.thermostat["ctAHFanCurrentDemandStatus"],
        }

    @property
    def is_aux_heat(self):
        """Return true if aux heater."""
        return False #TBD: Need to figure out how to determine if aux heat is running

    '''
    def set_preset_mode(self, preset_mode):
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return

        self.update_without_throttle = True

        # If we are currently in vacation mode, cancel it.
        if self.preset_mode == PRESET_VACATION:
            self.data.ecobee.delete_vacation(self.thermostat["id"], self.vacation)

        if preset_mode == PRESET_AWAY:
            self.data.ecobee.set_climate_hold(
                self.thermostat_index, "away", "indefinite"
            )

        elif preset_mode == PRESET_TEMPERATURE:
            self.set_temp_hold(self.current_temperature)

        elif preset_mode in (PRESET_HOLD_NEXT_TRANSITION, PRESET_HOLD_INDEFINITE):
            self.data.ecobee.set_climate_hold(
                self.thermostat_index,
                PRESET_TO_ECOBEE_HOLD[preset_mode],
                self.hold_preference(),
            )

        elif preset_mode == PRESET_NONE:
            self.data.ecobee.resume_program(self.thermostat_index)

        elif preset_mode in self.preset_modes:
            climate_ref = None

            for comfort in self.thermostat["program"]["climates"]:
                if comfort["name"] == preset_mode:
                    climate_ref = comfort["climateRef"]
                    break

            if climate_ref is not None:
                self.data.ecobee.set_climate_hold(
                    self.thermostat_index, climate_ref, self.hold_preference()
                )
            else:
                _LOGGER.warning("Received unknown preset mode: %s", preset_mode)

        else:
            self.data.ecobee.set_climate_hold(
                self.thermostat_index, preset_mode, self.hold_preference()
            )
    '''

    '''
    @property
    def preset_modes(self):
        """Return available preset modes."""
        return list(self._preset_modes.values())
    '''

    def set_auto_temp_hold(self, heat_temp, cool_temp):
        """Set temperature hold in auto mode."""
        if cool_temp is not None:
            cool_temp_setpoint = cool_temp
        else:
            cool_temp_setpoint = self.thermostat["cspHome"]

        if heat_temp is not None:
            heat_temp_setpoint = heat_temp
        else:
            heat_temp_setpoint = self.thermostat["hspHome"]

        self.data.daikinskyport.set_hold_temp(
            self.thermostat["id"],
            cool_temp_setpoint,
            heat_temp_setpoint,
            self.hold_preference(),
        )
        _LOGGER.debug(
            "Setting Daikin Skyport hold_temp to: heat=%s, is=%s, " "cool=%s, is=%s",
            heat_temp,
            isinstance(heat_temp, (int, float)),
            cool_temp,
            isinstance(cool_temp, (int, float)),
        )

        self.update_without_throttle = True

    def set_fan_mode(self, fan_mode):
        """Set the fan mode.  Valid values are "on" or "auto"."""
        if fan_mode.lower() != STATE_ON and fan_mode.lower() != HVAC_MODE_AUTO:
            error = "Invalid fan_mode value:  Valid values are 'on' or 'auto'"
            _LOGGER.error(error)
            return

        self.data.daikinskyport.set_fan_mode(
            self.thermostat["id"],
            fan_mode,
        )

        _LOGGER.info("Setting fan mode to: %s", fan_mode)

    def set_temp_hold(self, temp):
        """Set temperature hold in modes other than auto."""
        if self.hvac_mode == HVAC_MODE_HEAT:
            heat_temp = temp
            cool_temp = self.thermostat["cspHome"]
        elif self.hvac_mode == HVAC_MODE_COOL:
            cool_temp = temp
            heat_temp = self.thermostat["hspHome"]
        self.set_auto_temp_hold(heat_temp, cool_temp)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        low_temp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high_temp = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        temp = kwargs.get(ATTR_TEMPERATURE)

        if self.hvac_mode == HVAC_MODE_AUTO and (
            low_temp is not None or high_temp is not None
        ):
            self.set_auto_temp_hold(low_temp, high_temp)
        elif temp is not None:
            self.set_temp_hold(temp)
        else:
            _LOGGER.error("Missing valid arguments for set_temperature in %s", kwargs)

    def set_humidity(self, humidity):
        """Set the humidity level."""
        self.data.daikinskyport.set_humidity(self.thermostat["id"], humidity)

    def set_hvac_mode(self, hvac_mode):
        """Set HVAC mode (auto, auxHeatOnly, cool, heat, off)."""
        daikin_value = next(
            (k for k, v in DAIKIN_HVAC_TO_HASS.items() if v == hvac_mode), None
        )
        if daikin_value is None:
            _LOGGER.error("Invalid mode for set_hvac_mode: %s", hvac_mode)
            return
        self.data.daikinskyport.set_hvac_mode(self.thermostat["id"], daikin_value)
        self.update_without_throttle = True

    '''
    def set_fan_min_on_time(self, fan_min_on_time):
        """Set the minimum fan on time."""
        self.data.ecobee.set_fan_min_on_time(self.thermostat_index, fan_min_on_time)
        self.update_without_throttle = True
    '''

    def resume_program(self, resume_all):
        """Resume the thermostat schedule program."""
        self.data.daikinskyport.resume_program(
            self.thermostat["id"], "true"
        )
        self.update_without_throttle = True

    '''
    def hold_preference(self):
        """Return user preference setting for hold time."""
        # Values returned from thermostat are 'useEndTime4hour',
        # 'useEndTime2hour', 'nextTransition', 'indefinite', 'askMe'
        default = self.thermostat["settings"]["holdAction"]
        if default == "nextTransition":
            return default
        # add further conditions if other hold durations should be
        # supported; note that this should not include 'indefinite'
        # as an indefinite away hold is interpreted as away_mode
        return "nextTransition"
    '''