"""Daikin Skyport integration."""

from datetime import timedelta

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_NAME, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.util import Throttle
from homeassistant.helpers.entity import DeviceInfo

from .daikinskyport import DaikinSkyport, ExpiredTokenError
from .const import (
    _LOGGER,
    DOMAIN,
    MANUFACTURER,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    COORDINATOR,
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)
UNDO_UPDATE_LISTENER = "undo_update_listener"

NETWORK = None

PLATFORMS = [Platform.SENSOR, Platform.WEATHER, Platform.CLIMATE, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DaikinSkyport as config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info("Daikin Skyport Starting")

    email: str = entry.data[CONF_EMAIL]
    password: str = entry.data[CONF_PASSWORD]
    try:
        access_token: str = entry.data[CONF_ACCESS_TOKEN]
        refresh_token: str = entry.data[CONF_REFRESH_TOKEN]
    except (NameError, KeyError):
        _LOGGER.debug("Tokens not in config for Daikin Skyport")
        access_token = ""
        refresh_token = ""
    config = {
        "EMAIL": email,
        "PASSWORD": password,
        "ACCESS_TOKEN": access_token,
        "REFRESH_TOKEN": refresh_token,
    }

    assert entry.unique_id is not None
    unique_id = entry.unique_id

    _LOGGER.debug("Using email: %s", email)

    coordinator = DaikinSkyportData(hass, config, unique_id, entry)

    try:
        await coordinator._async_update_data()
    except ExpiredTokenError as ex:
        _LOGGER.warn(f"Unable to refresh auth token: {ex}")
        raise ConfigEntryNotReady("Unable to refresh token.")

    if coordinator.daikinskyport.thermostats is None:
        _LOGGER.error("No Daikin Skyport devices found to set up")
        return False

    #    entry.async_on_unload(entry.add_update_listener(update_listener))

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)

    undo_listener = entry.add_update_listener(update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unload Entry: %s", str(entry))
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("Reload Entry: %s", str(entry))
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    _LOGGER.debug("Update listener: %s", str(entry))


#    await hass.config_entries.async_reload(entry.entry_id)


class DaikinSkyportData:
    """Get the latest data and update the states."""

    def __init__(
        self, hass: HomeAssistant, config, unique_id: str, entry: ConfigEntry
    ) -> None:
        """Init the Daikin Skyport data object."""
        self.platforms = []
        try:
            self.name: str = entry.options[CONF_NAME]
        except (NameError, KeyError):
            self.name: str = entry.data[CONF_NAME]
        self.hass = hass
        self.entry = entry
        self.unique_id = unique_id
        self.daikinskyport = DaikinSkyport(config=config)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=self.name,
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def _async_update_data(self):
        """Update data via library."""
        try:
            await self.hass.async_add_executor_job(self.daikinskyport.update)
            _LOGGER.debug("Daikin Skyport _async_update_data")
        except ExpiredTokenError:
            _LOGGER.debug("Daikin Skyport tokens expired")
            await self.async_refresh()
            await self.hass.async_add_executor_job(self.daikinskyport.update)
        _LOGGER.debug("Daikin Skyport data updated successfully")
        return

    async def async_refresh(self) -> bool:
        """Refresh tokens and update config entry."""
        _LOGGER.debug("Refreshing Daikin Skyport tokens and updating config entry")
        if await self.hass.async_add_executor_job(self.daikinskyport.refresh_tokens):
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={
                    CONF_NAME: self.name,
                    CONF_REFRESH_TOKEN: self.daikinskyport.refresh_token,
                    CONF_ACCESS_TOKEN: self.daikinskyport.access_token,
                    CONF_EMAIL: self.daikinskyport.user_email,
                    CONF_PASSWORD: self.daikinskyport.user_password,
                },
            )
            return True
        _LOGGER.error("Error refreshing Daikin Skyport tokens")
        return False
