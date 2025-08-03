"""Support for displaying weather info from Daikin Skyport API."""

from datetime import timedelta

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_TIME,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import (
    UnitOfTemperature,
)
from homeassistant.util import dt as dt_util
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    _LOGGER,
    DAIKIN_WEATHER_ICON_TO_HASS,
    COORDINATOR,
    DOMAIN,
)
from . import DaikinSkyportData


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add a Daikin Skyport Weather entity from a config_entry."""

    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: DaikinSkyportData = data[COORDINATOR]

    for index in range(len(coordinator.daikinskyport.thermostats)):
        thermostat = coordinator.daikinskyport.get_thermostat(index)
        async_add_entities(
            [DaikinSkyportWeather(coordinator, thermostat["name"], index)], True
        )


class DaikinSkyportWeather(WeatherEntity):
    """Representation of Daikin Skyport weather data."""

    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, data, name, index):
        """Initialize the Daikin Skyport weather platform."""
        self.data = data
        self._name = name
        self._attr_unique_id = (
            f"{data.daikinskyport.thermostats[index]['id']}-{self._name}"
        )
        self._index = index
        self.weather = None

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units.

        Only implement this method if `WeatherEntityFeature.FORECAST_DAILY` is set
        """

        forecasts: list[Forecast] = []
        date = dt_util.utcnow()
        for day in ["Today", "Day1", "Day2", "Day3", "Day4", "Day5"]:
            forecast = {}
            try:
                forecast[ATTR_FORECAST_CONDITION] = DAIKIN_WEATHER_ICON_TO_HASS[
                    self.weather["weather" + day + "Icon"]
                ]
                forecast[ATTR_FORECAST_NATIVE_TEMP] = self.weather[
                    "weather" + day + "TempC"
                ]
                forecast[ATTR_FORECAST_HUMIDITY] = self.weather["weather" + day + "Hum"]
                _LOGGER.debug(
                    "Weather icon for weather%sIcon: %s",
                    day,
                    self.weather["weather" + day + "Icon"],
                )
            except (ValueError, IndexError, KeyError) as e:
                _LOGGER.error("Key not found for weather icon: %s", e)
                date += timedelta(days=1)
                continue
            if forecast is None:
                date += timedelta(days=1)
                continue
            forecast[ATTR_FORECAST_TIME] = date.isoformat()
            date += timedelta(days=1)
            forecasts.append(forecast)

        if forecasts:
            return forecasts
        return None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def condition(self):
        """Return the current condition."""
        try:
            _LOGGER.debug(
                "Weather icon for weatherTodayIcon: %s",
                self.weather["weatherTodayIcon"],
            )
            return DAIKIN_WEATHER_ICON_TO_HASS[self.weather["weatherTodayIcon"]]
        except KeyError as e:
            _LOGGER.error("Key not found for weather condition: %s", e)
            return None

    @property
    def native_temperature(self):
        """Return the temperature."""
        try:
            return float(self.weather["weatherTodayTempC"])
        except ValueError:
            return None

    @property
    def humidity(self):
        """Return the humidity."""
        try:
            return int(self.weather["weatherTodayHum"])
        except ValueError:
            return None

    @property
    def device_info(self) -> DeviceInfo:
        return self.data.device_info

    async def async_update(self) -> None:
        """Get the latest state of the sensor."""
        await self.data._async_update_data()
        self.weather = dict()
        thermostat = self.data.daikinskyport.get_thermostat(self._index)
        for key in thermostat:
            if key.startswith("weather"):
                self.weather[key] = thermostat[key]
        self.weather["tz"] = thermostat["timeZone"]
