"""Support for Daikin Skyport Thermostats."""

import collections
from datetime import datetime
from typing import Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_ON,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    STATE_ON,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DaikinSkyportData
from .const import (
    _LOGGER,
    COORDINATOR,
    DAIKIN_HVAC_MODE_AUTO,
    DAIKIN_HVAC_MODE_AUXHEAT,
    DAIKIN_HVAC_MODE_COOL,
    DAIKIN_HVAC_MODE_HEAT,
    DAIKIN_HVAC_MODE_OFF,
    DOMAIN,
)

WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Hold settings (manual mode)
HOLD_NEXT_TRANSITION = 0
HOLD_1HR = 60
HOLD_2HR = 120
HOLD_4HR = 240
HOLD_8HR = 480

# Preset values
PRESET_AWAY = "Away"
PRESET_SCHEDULE = "Schedule"
PRESET_MANUAL = "Manual"
PRESET_TEMP_HOLD = "Temp Hold"
FAN_SCHEDULE = "Schedule"

# Fan Schedule values
ATTR_FAN_START_TIME = "start_time"
ATTR_FAN_STOP_TIME = "end_time"
ATTR_FAN_INTERVAL = "interval"
ATTR_FAN_SPEED = "fan_speed"

# Night Mode values
ATTR_NIGHT_MODE_START_TIME = "start_time"
ATTR_NIGHT_MODE_END_TIME = "end_time"
ATTR_NIGHT_MODE_ENABLE = "enable"

# Schedule Adjustment values
ATTR_SCHEDULE_DAY = "day"
ATTR_SCHEDULE_START_TIME = "start_time"
ATTR_SCHEDULE_PART = "part"
ATTR_SCHEDULE_PART_ENABLED = "enable"
ATTR_SCHEDULE_PART_LABEL = "label"
ATTR_SCHEDULE_HEATING_SETPOINT = "heat_temp_setpoint"
ATTR_SCHEDULE_COOLING_SETPOINT = "cool_temp_setpoint"
ATTR_SCHEDULE_MODE = "mode"  # Unknown what this does right now
ATTR_SCHEDULE_ACTION = "action"  # Unknown what this does right now

# OneClean values
ATTR_ONECLEAN_ENABLED = "enable"

# Efficiency value
ATTR_EFFICIENCY_ENABLED = "enable"

# Order matters, because for reverse mapping we don't want to map HEAT to AUX
DAIKIN_HVAC_TO_HASS = collections.OrderedDict(
    [
        (DAIKIN_HVAC_MODE_HEAT, HVACMode.HEAT),
        (DAIKIN_HVAC_MODE_COOL, HVACMode.COOL),
        (DAIKIN_HVAC_MODE_AUTO, HVACMode.AUTO),
        (DAIKIN_HVAC_MODE_OFF, HVACMode.OFF),
        (DAIKIN_HVAC_MODE_AUXHEAT, HVACMode.HEAT),
    ]
)

DAIKIN_FAN_TO_HASS = collections.OrderedDict(
    [
        (0, FAN_AUTO),
        (1, FAN_ON),
        (2, FAN_SCHEDULE),
        (3, FAN_LOW),
        (4, FAN_MEDIUM),
        (5, FAN_HIGH),
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
    1: HVACAction.COOLING,
    3: HVACAction.HEATING,
    4: HVACAction.FAN,
    2: HVACAction.DRYING,
    5: HVACAction.IDLE,
}

PRESET_TO_DAIKIN_HOLD = {
    HOLD_NEXT_TRANSITION: 0,
    HOLD_1HR: 60,
    HOLD_2HR: 120,
    HOLD_4HR: 240,
    HOLD_8HR: 480,
}

SERVICE_RESUME_PROGRAM = "daikin_resume_program"
SERVICE_SET_FAN_SCHEDULE = "daikin_set_fan_schedule"
SERVICE_SET_NIGHT_MODE = "daikin_set_night_mode"
SERVICE_SET_THERMOSTAT_SCHEDULE = "daikin_set_thermostat_schedule"
SERVICE_SET_ONECLEAN = "daikin_set_oneclean"
SERVICE_PRIORITIZE_EFFICIENCY = "daikin_prioritize_efficiency"

RESUME_PROGRAM_SCHEMA = vol.Schema({vol.Optional(ATTR_ENTITY_ID): cv.entity_ids})

FAN_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_FAN_START_TIME): cv.positive_int,
        vol.Optional(ATTR_FAN_STOP_TIME): cv.positive_int,
        vol.Optional(ATTR_FAN_INTERVAL): cv.positive_int,
        vol.Optional(ATTR_FAN_SPEED): cv.positive_int,
    }
)

NIGHT_MODE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_NIGHT_MODE_START_TIME): cv.positive_int,
        vol.Optional(ATTR_NIGHT_MODE_END_TIME): cv.positive_int,
        vol.Optional(ATTR_NIGHT_MODE_ENABLE): cv.boolean,
    }
)

THERMOSTAT_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_SCHEDULE_DAY): cv.string,
        vol.Optional(ATTR_SCHEDULE_START_TIME): cv.positive_int,
        vol.Optional(ATTR_SCHEDULE_PART): cv.positive_int,
        vol.Optional(ATTR_SCHEDULE_PART_ENABLED): cv.boolean,
        vol.Optional(ATTR_SCHEDULE_PART_LABEL): cv.string,
        vol.Optional(ATTR_SCHEDULE_HEATING_SETPOINT): cv.positive_int,
        vol.Optional(ATTR_SCHEDULE_COOLING_SETPOINT): cv.positive_int,
    }
)

ONECLEAN_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_ONECLEAN_ENABLED): cv.boolean,
    }
)

EFFICIENCY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(ATTR_EFFICIENCY_ENABLED): cv.boolean,
    }
)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add a Daikin Skyport Climate entity from a config_entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DaikinSkyportData = data[COORDINATOR]
    entities = []

    for index in range(len(coordinator.daikinskyport.thermostats)):
        thermostat = coordinator.daikinskyport.get_thermostat(index)
        entities.append(Thermostat(coordinator, index, thermostat))

    async_add_entities(entities, True)

    def resume_program_set_service(service: ServiceCall) -> None:
        """Resume the schedule on the target thermostats."""
        entity_ids = service.data[ATTR_ENTITY_ID]

        _LOGGER.info("Resuming program for %s", entity_ids)

        for entity in entity_ids:
            for thermostat in entities:
                if thermostat.entity_id == entity:
                    thermostat.resume_program()
                    _LOGGER.info("Program resumed for %s", entity)
                    thermostat.schedule_update_ha_state(True)
                    break

    def set_fan_schedule_service(service):
        """Set the fan schedule on the target thermostats."""

        start = service.data.get(ATTR_FAN_START_TIME)
        stop = service.data.get(ATTR_FAN_STOP_TIME)
        interval = service.data.get(ATTR_FAN_INTERVAL)
        speed = service.data.get(ATTR_FAN_SPEED)

        entity_ids = service.data[ATTR_ENTITY_ID]

        _LOGGER.info("Setting fan schedule for %s", entity_ids)

        for entity in entity_ids:
            for thermostat in entities:
                if thermostat.entity_id == entity:
                    thermostat.set_fan_schedule(start, stop, interval, speed)
                    _LOGGER.info("Fan schedule set for %s", entity)
                    thermostat.schedule_update_ha_state(True)
                    break

    def set_night_mode_service(service):
        """Set night mode on the target thermostats."""

        start = service.data.get(ATTR_NIGHT_MODE_START_TIME)
        stop = service.data.get(ATTR_NIGHT_MODE_END_TIME)
        enable = service.data.get(ATTR_NIGHT_MODE_ENABLE)

        entity_ids = service.data[ATTR_ENTITY_ID]

        _LOGGER.info("Setting night mode for %s", entity_ids)

        for entity in entity_ids:
            for thermostat in entities:
                if thermostat.entity_id == entity:
                    thermostat.set_night_mode(start, stop, enable)
                    _LOGGER.info("Night mode set for %s", entity)
                    thermostat.schedule_update_ha_state(True)
                    break

    def set_thermostat_schedule_service(service):
        """Set the thermostat schedule on the target thermostats."""
        day = service.data.get(ATTR_SCHEDULE_DAY)
        start = service.data.get(ATTR_SCHEDULE_START_TIME)
        part = service.data.get(ATTR_SCHEDULE_PART)
        enable = service.data.get(ATTR_SCHEDULE_PART_ENABLED)
        label = service.data.get(ATTR_SCHEDULE_PART_LABEL)
        heating = service.data.get(ATTR_SCHEDULE_HEATING_SETPOINT)
        cooling = service.data.get(ATTR_SCHEDULE_COOLING_SETPOINT)

        entity_ids = service.data[ATTR_ENTITY_ID]

        _LOGGER.info("Setting thermostat schedule for %s", entity_ids)

        for entity in entity_ids:
            for thermostat in entities:
                if thermostat.entity_id == entity:
                    thermostat.set_thermostat_schedule(
                        day, start, part, enable, label, heating, cooling
                    )
                    _LOGGER.info("Thermostat schedule set for %s", entity)
                    thermostat.schedule_update_ha_state(True)
                    break

    def set_oneclean_service(service):
        """Enable/disable OneClean."""
        enable = service.data.get(ATTR_ONECLEAN_ENABLED)

        entity_ids = service.data[ATTR_ENTITY_ID]

        _LOGGER.info("Setting OneClean for %s", entity_ids)

        for entity in entity_ids:
            for thermostat in entities:
                if thermostat.entity_id == entity:
                    thermostat.set_oneclean(enable)
                    _LOGGER.info("OneClean set for %s", entity)
                    thermostat.schedule_update_ha_state(True)
                    break

    def set_efficiency_service(service):
        """Enable/disable heat pump efficiency."""
        enable = service.data.get(ATTR_EFFICIENCY_ENABLED)

        entity_ids = service.data[ATTR_ENTITY_ID]

        _LOGGER.info("Setting efficiency for %s", entity_ids)

        for entity in entity_ids:
            for thermostat in entities:
                if thermostat.entity_id == entity:
                    thermostat.set_efficiency(enable)
                    _LOGGER.info("Efficiency set for %s", entity)
                    thermostat.schedule_update_ha_state(True)
                    break

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESUME_PROGRAM,
        resume_program_set_service,
        schema=RESUME_PROGRAM_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SCHEDULE,
        set_fan_schedule_service,
        schema=FAN_SCHEDULE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_NIGHT_MODE,
        set_night_mode_service,
        schema=NIGHT_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_THERMOSTAT_SCHEDULE,
        set_thermostat_schedule_service,
        schema=THERMOSTAT_SCHEDULE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ONECLEAN,
        set_oneclean_service,
        schema=ONECLEAN_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PRIORITIZE_EFFICIENCY,
        set_efficiency_service,
        schema=EFFICIENCY_SCHEMA,
    )


class Thermostat(ClimateEntity):
    """A thermostat class for Daikin Skyport Thermostats."""

    _attr_precision = PRECISION_TENTHS
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_fan_modes = [FAN_AUTO, FAN_ON, FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_SCHEDULE]
    _attr_name = None
    _attr_has_entity_name = True
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, data, thermostat_index, thermostat):
        """Initialize the thermostat."""
        self.data = data
        self.thermostat_index = thermostat_index
        self.thermostat = thermostat
        self._name = self.thermostat["name"]
        self._attr_unique_id = f"{self.thermostat['id']}-climate"
        self._cool_setpoint = self.thermostat["cspActive"]
        self._heat_setpoint = self.thermostat["hspActive"]
        self._hvac_mode = DAIKIN_HVAC_TO_HASS[self.thermostat["mode"]]
        if DAIKIN_FAN_TO_HASS[self.thermostat["fanCirculate"]] == FAN_ON:
            self._fan_mode = DAIKIN_FAN_TO_HASS[
                self.thermostat["fanCirculateSpeed"] + 3
            ]
        else:
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
        if self.thermostat["ctSystemCapHeat"]:
            self._operation_list.append(HVACMode.HEAT)
        if (
            "ctOutdoorNoofCoolStages" in self.thermostat
            and self.thermostat["ctOutdoorNoofCoolStages"] > 0
        ) or (
            "P1P2S21CoolingCapability" in self.thermostat
            and self.thermostat["P1P2S21CoolingCapability"] is True
        ):
            self._operation_list.append(HVACMode.COOL)
        if len(self._operation_list) == 2:
            self._operation_list.insert(0, HVACMode.AUTO)
        self._operation_list.append(HVACMode.OFF)

        self._preset_modes = {
            PRESET_SCHEDULE,
            PRESET_MANUAL,
            PRESET_TEMP_HOLD,
            PRESET_AWAY,
        }
        self._fan_modes = [
            FAN_AUTO,
            FAN_ON,
            FAN_LOW,
            FAN_MEDIUM,
            FAN_HIGH,
            FAN_SCHEDULE,
        ]
        self.update_without_throttle = False

    async def async_update(self):
        """Get the latest state from the thermostat."""
        if self.update_without_throttle:
            await self.data._async_update_data(no_throttle=True)
            self.update_without_throttle = False
        else:
            await self.data._async_update_data()

        self.thermostat = self.data.daikinskyport.get_thermostat(self.thermostat_index)
        self._cool_setpoint = self.thermostat["cspActive"]
        self._heat_setpoint = self.thermostat["hspActive"]
        self._hvac_mode = DAIKIN_HVAC_TO_HASS[self.thermostat["mode"]]
        if DAIKIN_FAN_TO_HASS[self.thermostat["fanCirculate"]] == FAN_ON:
            self._fan_mode = DAIKIN_FAN_TO_HASS[
                self.thermostat["fanCirculateSpeed"] + 3
            ]
        else:
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
    def device_info(self) -> DeviceInfo:
        return self.data.device_info

    @property
    def available(self):
        """Return if device is available."""
        return True  # TBD: Need to determine how to tell if the thermostat is available or not

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the Daikin Thermostat."""
        return self.thermostat["name"]

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self.thermostat["tempIndoor"]

    @property
    def target_temperature_low(self):
        """Return the lower bound temperature we try to reach."""
        if self.hvac_mode == HVACMode.AUTO:
            return self._heat_setpoint
        return None

    @property
    def target_temperature_high(self):
        """Return the upper bound temperature we try to reach."""
        if self.hvac_mode == HVACMode.AUTO:
            return self._cool_setpoint
        return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self.hvac_mode == HVACMode.AUTO:
            return None
        if self.hvac_mode == HVACMode.HEAT:
            return self._heat_setpoint
        if self.hvac_mode == HVACMode.COOL:
            return self._cool_setpoint
        return None

    @property
    def fan(self):
        """Return the current fan status."""
        if (
            "ctAHFanCurrentDemandStatus" in self.thermostat
            and self.thermostat["ctAHFanCurrentDemandStatus"] > 0
        ):
            return STATE_ON
        return HVACMode.OFF

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
    def extra_state_attributes(self):
        """Return device specific state attributes."""
        fan_cfm = "Unavailable"
        fan_demand = "Unavailable"
        cooling_demand = "Unavailable"
        heating_demand = "Unavailable"
        heatpump_demand = "Unavailable"
        dehumidification_demand = "Unavailable"
        humidification_demand = "Unavailable"
        indoor_mode = "Unavailable"

        if "ctAHCurrentIndoorAirflow" in self.thermostat:
            if self.thermostat["ctAHCurrentIndoorAirflow"] == 65535:
                fan_cfm = self.thermostat["ctIFCIndoorBlowerAirflow"]
            else:
                fan_cfm = self.thermostat["ctAHCurrentIndoorAirflow"]

        if "ctAHFanCurrentDemandStatus" in self.thermostat:
            fan_demand = round(self.thermostat["ctAHFanCurrentDemandStatus"] / 2, 1)

        if "ctOutdoorCoolRequestedDemand" in self.thermostat:
            cooling_demand = round(
                self.thermostat["ctOutdoorCoolRequestedDemand"] / 2, 1
            )

        if "ctAHHeatRequestedDemand" in self.thermostat:
            heating_demand = round(self.thermostat["ctAHHeatRequestedDemand"] / 2, 1)

        if "ctOutdoorHeatRequestedDemand" in self.thermostat:
            heatpump_demand = round(
                self.thermostat["ctOutdoorHeatRequestedDemand"] / 2, 1
            )

        if "ctOutdoorDeHumidificationRequestedDemand" in self.thermostat:
            dehumidification_demand = round(
                self.thermostat["ctOutdoorDeHumidificationRequestedDemand"] / 2, 1
            )

        if "ctAHHumidificationRequestedDemand" in self.thermostat:
            humidification_demand = round(
                self.thermostat["ctAHHumidificationRequestedDemand"] / 2, 1
            )

        if "ctAHUnitType" in self.thermostat and self.thermostat["ctAHUnitType"] != 255:
            indoor_mode = self.thermostat["ctAHMode"].strip()
        elif (
            "ctIFCUnitType" in self.thermostat
            and self.thermostat["ctIFCUnitType"] != 255
        ):
            indoor_mode = self.thermostat["ctIFCOperatingHeatCoolMode"].strip()

        outdoor_mode = "Unavailable"
        if "ctOutdoorMode" in self.thermostat:
            outdoor_mode = self.thermostat["ctOutdoorMode"].strip()

        return {
            "fan": self.fan,
            "schedule_mode": self.thermostat["schedEnabled"],
            "fan_cfm": fan_cfm,
            "fan_demand": fan_demand,
            "cooling_demand": cooling_demand,
            "heating_demand": heating_demand,
            "heatpump_demand": heatpump_demand,
            "dehumidification_demand": dehumidification_demand,
            "humidification_demand": humidification_demand,
            "thermostat_version": self.thermostat["statFirmware"],
            "night_mode_active": self.thermostat["nightModeActive"],
            "night_mode_enabled": self.thermostat["nightModeEnabled"],
            "indoor_mode": indoor_mode,
            "outdoor_mode": outdoor_mode,
            "thermostat_unlocked": bool(self.thermostat["displayLockPIN"] == 0),
            "media_filter_days": self.thermostat["alertMediaAirFilterDays"],
        }

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
            self.data.daikinskyport.set_permanent_hold(self.thermostat_index)

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

        if self._preset_mode == PRESET_MANUAL:
            self.data.daikinskyport.set_permanent_hold(
                self.thermostat_index, cool_temp_setpoint, heat_temp_setpoint
            )
        else:
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
        """Set the fan mode.  Valid values are "on", "auto", or "schedule"."""
        if fan_mode in {FAN_ON, FAN_AUTO, FAN_SCHEDULE}:
            self.data.daikinskyport.set_fan_mode(
                self.thermostat_index, FAN_TO_DAIKIN_FAN[fan_mode]
            )

            self._fan_mode = fan_mode
            self.update_without_throttle = True

            _LOGGER.debug("Setting fan mode to: %s", fan_mode)
        elif fan_mode in {FAN_LOW, FAN_MEDIUM, FAN_HIGH}:
            # Start the fan if it's off.
            if self._fan_mode == FAN_AUTO:
                self.data.daikinskyport.set_fan_mode(
                    self.thermostat_index, FAN_TO_DAIKIN_FAN[FAN_ON]
                )

                self._fan_mode = fan_mode

                _LOGGER.debug("Setting fan mode to: %s", fan_mode)

            self.data.daikinskyport.set_fan_speed(
                self.thermostat_index, FAN_TO_DAIKIN_FAN[fan_mode]
            )

            self._fan_speed = FAN_TO_DAIKIN_FAN[fan_mode]
            self.update_without_throttle = True

            _LOGGER.debug("Setting fan speed to: %s", self._fan_speed)
        else:
            error = (
                "Invalid fan_mode value:  Valid values are 'on', 'auto', or 'schedule'"
            )
            _LOGGER.error(error)
            return

    def set_temp_hold(self, temp):
        """Set temperature hold in modes other than auto."""
        if self.hvac_mode == HVACMode.HEAT:
            heat_temp = temp
            cool_temp = self.thermostat["cspHome"]
        elif self.hvac_mode == HVACMode.COOL:
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

        if self.hvac_mode == HVACMode.AUTO and (
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
        self.data.daikinskyport.resume_program(self.thermostat_index)
        self.update_without_throttle = True

    def set_fan_schedule(self, start=None, stop=None, interval=None, speed=None):
        """Set the thermostat fan schedule."""
        if start is None:
            start = self.thermostat["fanCirculateStart"]
        if stop is None:
            stop = self.thermostat["fanCirculateStop"]
        if interval is None:
            interval = self.thermostat["fanCirculateDuration"]
        self.data.daikinskyport.set_fan_schedule(
            self.thermostat_index, start, stop, interval, speed
        )
        self.update_without_throttle = True

    def set_night_mode(self, start=None, stop=None, enable=None):
        """Set the thermostat night mode."""
        if start is None:
            start = self.thermostat["nightModeStart"]
        if stop is None:
            stop = self.thermostat["nightModeStop"]
        if enable is None:
            enable = self.thermostat["nightModeEnabled"]
        self.data.daikinskyport.set_night_mode(
            self.thermostat_index, start, stop, enable
        )
        self.update_without_throttle = True

    def set_thermostat_schedule(
        self,
        day=None,
        start=None,
        part=None,
        enable=None,
        label=None,
        heating=None,
        cooling=None,
    ):
        """Set the thermostat schedule."""
        if day is None:
            now = datetime.now()
            day = now.strftime("%a")
        else:
            day = day[0:3].capitalize()
            if day not in WEEKDAY:
                _LOGGER.error("Invalid weekday: %s", day)
                return None
        if part is None:
            part = 1
        prefix = "sched" + day + "Part" + str(part)
        if start is None:
            start = self.thermostat[prefix + "Time"]
        if enable is None:
            enable = self.thermostat[prefix + "Enabled"]
        if label is None:
            label = self.thermostat[prefix + "Label"]
        if heating is None:
            heating = self.thermostat[prefix + "hsp"]
        if cooling is None:
            cooling = self.thermostat[prefix + "csp"]
        self.data.daikinskyport.set_thermostat_schedule(
            self.thermostat_index, prefix, start, enable, label, heating, cooling
        )
        self.update_without_throttle = True

    def set_oneclean(self, enable):
        """Enable/disable OneClean."""
        self.data.daikinskyport.set_fan_clean(self.thermostat_index, enable)
        self.update_without_throttle = True

    def set_efficiency(self, enable):
        """Enable/disable heat pump efficiency."""
        self.data.daikinskyport.set_dual_fuel_efficiency(self.thermostat_index, enable)
        self.update_without_throttle = True

    def hold_preference(self):
        """Return user preference setting for hold time."""
        default = self.thermostat["schedOverrideDuration"]
        if isinstance(default, int):
            return default
        return HOLD_NEXT_TRANSITION
