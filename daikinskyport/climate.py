"""Support for Daikin Skyport Thermostats."""
import collections
from time import sleep
from typing import Optional

import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
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
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
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

from .const import (
    _LOGGER,
    DOMAIN,
)

#Hold settings (manual mode)
HOLD_NEXT_TRANSITION = 0
HOLD_1HR = 60
HOLD_2HR = 120
HOLD_4HR = 240
HOLD_8HR = 480

#Preset values
PRESET_AWAY = "Away"
PRESET_SCHEDULE = "Schedule"
PRESET_MANUAL = "Manual"
PRESET_TEMP_HOLD = "Temp Hold"
FAN_SCHEDULE = "Schedule"

#Fan Schedule values
ATTR_FAN_START_TIME = "start_time"
ATTR_FAN_STOP_TIME = "stop_time"
ATTR_FAN_INTERVAL = "interval"

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
        (2, FAN_SCHEDULE),
    ]
)

DAIKIN_FAN_SPEED_TO_HASS = collections.OrderedDict(
    [
        (0, FAN_LOW),
        (1, FAN_MEDIUM),
        (2, FAN_HIGH),
    ]
)

FAN_TO_DAIKIN_FAN = collections.OrderedDict(
    [
        (FAN_AUTO, 0),
        (FAN_ON, 1),
        (FAN_SCHEDULE, 2),
        (FAN_LOW, 0),
        (FAN_MEDIUM, 1),
        (FAN_HIGH, 2),
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

PRESET_TO_DAIKIN_HOLD = {
    HOLD_NEXT_TRANSITION: 0,
    HOLD_1HR: 60,
    HOLD_2HR: 120,
    HOLD_4HR: 240,
    HOLD_8HR: 480
}

SERVICE_RESUME_PROGRAM = "daikin_resume_program"
SERVICE_SET_FAN_SCHEDULE = "daikin_set_fan_schedule"

RESUME_PROGRAM_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids
    }
)

FAN_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_FAN_START_TIME): cv.string,
        vol.Optional(ATTR_FAN_STOP_TIME): cv.string,
        vol.Optional(ATTR_FAN_INTERVAL): cv.positive_int
    }
)

SUPPORT_FLAGS = (
    SUPPORT_TARGET_TEMPERATURE
    | SUPPORT_PRESET_MODE
    | SUPPORT_AUX_HEAT
    | SUPPORT_TARGET_TEMPERATURE_RANGE
    | SUPPORT_FAN_MODE
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Daikin Skyport Thermostat Platform."""
    if discovery_info is None:
        return
    data = hass.data[DOMAIN]
    
    devices = [
        Thermostat(data, index)
        for index in range(len(data.daikinskyport.thermostats))
    ]
    add_entities(devices)

    def resume_program_set_service(service):
        """Resume the schedule on the target thermostats."""
        entity_id = service.data.get(ATTR_ENTITY_ID)

        if entity_id:
            target_thermostats = [
                device for device in devices if device.entity_id in entity_id
            ]
        else:
            target_thermostats = devices

        for thermostat in target_thermostats:
            thermostat.resume_program(thermostat["id"])

            thermostat.schedule_update_ha_state(True)

    def set_fan_schedule_service(service):
        """Set the fan schedule on the target thermostats."""
        entity_id = service.data.get(ATTR_ENTITY_ID)
        
        start = service.data.get(ATTR_FAN_START_TIME)
        stop = service.data.get(ATTR_FAN_STOP_TIME)
        interval = service.data.get(ATTR_FAN_INTERVAL)

        if entity_id:
            target_thermostats = [
                device for device in devices if device.entity_id in entity_id
            ]
        else:
            target_thermostats = devices

        for thermostat in target_thermostats:
            thermostat.set_fan_schedule(start, stop, interval)

            thermostat.schedule_update_ha_state(True)

    hass.services.register(
        DOMAIN,
        SERVICE_RESUME_PROGRAM,
        resume_program_set_service,
        schema=RESUME_PROGRAM_SCHEMA,
    )

    hass.services.register(
        DOMAIN,
        SERVICE_SET_FAN_SCHEDULE,
        set_fan_schedule_service,
        schema=FAN_SCHEDULE_SCHEMA,
    )

class Thermostat(ClimateEntity):
    """A thermostat class for Daikin Skyport Thermostats."""

    def __init__(self, data, thermostat_index):
        """Initialize the thermostat."""
        self.data = data
        self.thermostat_index = thermostat_index
        self.thermostat = self.data.daikinskyport.get_thermostat(self.thermostat_index)
        self._name = self.thermostat["name"]
        self._cool_setpoint = self.thermostat["cspActive"]
        self._heat_setpoint = self.thermostat["hspActive"]
        self._hvac_mode = DAIKIN_HVAC_TO_HASS[self.thermostat["mode"]]
        self._fan_mode = DAIKIN_FAN_TO_HASS[self.thermostat["fanCirculate"]]
        self._fan_speed = DAIKIN_FAN_SPEED_TO_HASS[self.thermostat["fanCirculateSpeed"]]
        if self.thermostat["geofencingAway"]:
            self._preset_mode = PRESET_AWAY
        elif self.thermostat["schedOverride"] == 1:
            self._preset_mode = PRESET_TEMP_HOLD
        elif self.thermostat["schedEnabled"]:
            self._preset_mode = PRESET_SCHEDULE
        else:
            self._preset_mode = PRESET_MANUAL

        self._operation_list = []
        if self.thermostat["ctSystemCapEmergencyHeat"] or (self.thermostat["ctOutdoorNoofHeatStates"] > 0):
            self._operation_list.append(HVAC_MODE_HEAT)
        if (self.thermostat["ctOutdoorNoofCoolStages"] > 0):
            self._operation_list.append(HVAC_MODE_COOL)
        if len(self._operation_list) == 2:
            self._operation_list.insert(0, HVAC_MODE_AUTO)
        self._operation_list.append(HVAC_MODE_OFF)

        self._preset_modes = {PRESET_SCHEDULE,
                              PRESET_MANUAL,
                              PRESET_TEMP_HOLD,
                              PRESET_AWAY
                              }
        self._fan_modes = [FAN_AUTO, FAN_ON, FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_SCHEDULE]
        self.update_without_throttle = False

    def update(self):
        """Get the latest state from the thermostat."""
        if self.update_without_throttle:
            sleep(3)
            self.data.update(no_throttle=True)
            self.update_without_throttle = False
        else:
            self.data.update()

        self.thermostat = self.data.daikinskyport.get_thermostat(self.thermostat_index)
        self._cool_setpoint = self.thermostat["cspActive"]
        self._heat_setpoint = self.thermostat["hspActive"]
        self._hvac_mode = DAIKIN_HVAC_TO_HASS[self.thermostat["mode"]]
        self._fan_mode = DAIKIN_FAN_TO_HASS[self.thermostat["fanCirculate"]]
        self._fan_speed = DAIKIN_FAN_SPEED_TO_HASS[self.thermostat["fanCirculateSpeed"]]
        if self.thermostat["geofencingAway"]:
            self._preset_mode = PRESET_AWAY
        elif self.thermostat["schedOverride"] == 1:
            self._preset_mode = PRESET_TEMP_HOLD
        elif self.thermostat["schedEnabled"]:
            self._preset_mode = PRESET_SCHEDULE
        else:
            self._preset_mode = PRESET_MANUAL

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
        """Return the name of the Daikin Thermostat."""
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
            return self._heat_setpoint
        return None

    @property
    def target_temperature_high(self):
        """Return the upper bound temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_AUTO:
            return self._cool_setpoint
        return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVAC_MODE_AUTO:
            return None
        if self.hvac_mode == HVAC_MODE_HEAT:
            return self._heat_setpoint
        if self.hvac_mode == HVAC_MODE_COOL:
            return self._cool_setpoint
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
        return self._fan_mode

    @property
    def fan_speed(self):
        """Return the fan setting."""
        return self._fan_speed

    @property
    def fan_modes(self):
        """Return the available fan modes."""
        return self._fan_modes

    @property
    def preset_mode(self):
        """Return current preset mode."""
        return self._preset_mode

    @property
    def hvac_mode(self):
        """Return current operation."""
        return self._hvac_mode

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
            "fan_demand": round(self.thermostat["ctAHFanCurrentDemandStatus"] / 2, 1),
            "cooling_demand": round(self.thermostat["ctOutdoorCoolRequestedDemand"] / 2, 1),
            "heating_demand": round(self.thermostat["ctAHHeatRequestedDemand"] / 2, 1),
            "heatpump_demand": round(self.thermostat["ctOutdoorHeatRequestedDemand"] / 2, 1),
            "dehumidification_demand": round(self.thermostat["ctOutdoorDeHumidificationRequestedDemand"] / 2, 1),
            "humidification_demand": round(self.thermostat["ctAHHumidificationRequestedDemand"] / 2, 1),
            "thermostat_version": self.thermostat["statFirmware"],            
        }

    @property
    def is_aux_heat(self):
        """Return true if aux heater."""
        return False #TBD: Need to figure out how to determine if aux heat is running

    def set_preset_mode(self, preset_mode):
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return

        if preset_mode == PRESET_AWAY:
            self.data.daikinskyport.set_away(self.thermostat_index, True)

        elif preset_mode == PRESET_SCHEDULE:
            self.data.daikinskyport.set_away(self.thermostat_index, False)
            self.resume_program()

        elif preset_mode == PRESET_MANUAL:
            self.data.daikinskyport.set_away(self.thermostat_index, False)
            self.data.daikinskyport.set_permanent_hold(self.thermostat_index, False)
            
        elif preset_mode == PRESET_TEMP_HOLD:
            self.data.daikinskyport.set_away(self.thermostat_index, False)
            self.data.daikinskyport.set_temp_hold(self.thermostat_index)
        else:
            return
        
        self._preset_mode = preset_mode

        self.update_without_throttle = True

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return list(self._preset_modes)

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

        self.data.daikinskyport.set_temp_hold(
            self.thermostat_index,
            cool_temp_setpoint,
            heat_temp_setpoint,
            self.hold_preference(),
        )
        
        self._cool_setpoint = cool_temp_setpoint
        self._heat_setpoint = heat_temp_setpoint
        
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
        if fan_mode in {FAN_ON, FAN_AUTO, FAN_SCHEDULE}:
                self.data.daikinskyport.set_fan_mode(
                self.thermostat_index,
                FAN_TO_DAIKIN_FAN[fan_mode]
            )
            
            self._fan_mode = fan_mode
            self.update_without_throttle = True

            _LOGGER.info("Setting fan mode to: %s", fan_mode)
        elif fan_mode in {FAN_LOW, FAN_MEDIUM, FAN_HIGH}:
            # Start the fan if it's off.  
            if self._fan_mode == FAN_AUTO:
                self.data.daikinskyport.set_fan_mode(
                    self.thermostat_index,
                    FAN_TO_DAIKIN_FAN[FAN_ON]
                )
                
                self._fan_mode = fan_mode

                _LOGGER.info("Setting fan mode to: %s", fan_mode)

            self.data.daikinskyport.set_fan_speed(
                self.thermostat_index,
                FAN_TO_DAIKIN_FAN[fan_mode]
            )
            
            self._fan_speed = FAN_TO_DAIKIN_FAN[fan_mode]
            self.update_without_throttle = True

            _LOGGER.info("Setting fan speed to: %s", self._fan_speed)
        else:
            error = "Invalid fan_mode value:  Valid values are 'on' or 'auto'"
            _LOGGER.error(error)
            return


    def set_temp_hold(self, temp):
        """Set temperature hold in modes other than auto."""
        if self.hvac_mode == HVAC_MODE_HEAT:
            heat_temp = temp
            cool_temp = self.thermostat["cspHome"]
        elif self.hvac_mode == HVAC_MODE_COOL:
            cool_temp = temp
            heat_temp = self.thermostat["hspHome"]
        self.set_auto_temp_hold(heat_temp, cool_temp)

        self._cool_setpoint = cool_temp
        self._heat_setpoint = heat_temp

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

        self._cool_setpoint = high_temp
        self._heat_setpoint = low_temp


    def set_humidity(self, humidity):
        """Set the humidity level."""
        self.data.daikinskyport.set_humidity(self.thermostat_index, humidity)

    def set_hvac_mode(self, hvac_mode):
        """Set HVAC mode (auto, auxHeatOnly, cool, heat, off)."""
        daikin_value = next(
            (k for k, v in DAIKIN_HVAC_TO_HASS.items() if v == hvac_mode), None
        )
        if daikin_value is None:
            _LOGGER.error("Invalid mode for set_hvac_mode: %s", hvac_mode)
            return
        self.data.daikinskyport.set_hvac_mode(self.thermostat_index, daikin_value)
        self._hvac_mode = hvac_mode
        self.update_without_throttle = True

    def resume_program(self):
        """Resume the thermostat schedule program."""
        self.data.daikinskyport.resume_program(
            self.thermostat_index
        )
        self.update_without_throttle = True

    def set_fan_schedule(self, start=None, stop=None, interval=None):
        """Set the thermostat fan schedule."""
        if start is None:
            start = self.thermostat["fanCirculateStart"]
        if stop is None:
            stop = self.thermostat["fanCirculateStop"]
        if interval is None:
            interval = self.thermostat["fanCirculateDuration"]
        self.data.daikinskyport.set_fan_schedule(
            self.thermostat_index, start, stop, interval
        )
        self.update_without_throttle = True

    def hold_preference(self):
        """Return user preference setting for hold time."""
        default = self.thermostat["schedOverrideDuration"]
        if isinstance(default, int):
            return default
        return HOLD_NEXT_TRANSITION
