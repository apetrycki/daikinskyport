"""Daikin Skyport integration."""
import os
from datetime import timedelta
from async_timeout import timeout
from requests.exceptions import RequestException
from typing import Any
from aiohttp import ClientSession

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL,
    CONF_NAME,
    Platform
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import Throttle
from homeassistant.helpers.json import save_json
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo

from .daikinskyport import DaikinSkyport
from .const import (
    _LOGGER,
    DOMAIN,
    MANUFACTURER,
)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

NETWORK = None

PLATFORMS = [Platform.SENSOR, Platform.WEATHER, Platform.CLIMATE]


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_EMAIL): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DaikinSkyport as config entry."""
    email: str = entry.data[CONF_EMAIL]
    password: str = entry.data[CONF_PASSWORD]
    name: str = entry.data[CONF_NAME]
    assert entry.unique_id is not None
    unique_id = entry.unique_id

    _LOGGER.debug("Using email: %s", email)

    websession = async_get_clientsession(hass)

    coordinator = DaikinSkyportData(
        hass, websession, email, password, unique_id, name
    )
    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


class DaikinSkyportData(DataUpdateCoordinator[dict[str, Any]]):
    """Get the latest data and update the states."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        session: ClientSession, 
        email: str, 
        password: str, 
        unique_id: str,
        name: str) -> None:
        """Init the Daikin Skyport data object."""
        self.unique_id = unique_id
        self.daikinskyport = DaikinSkyport(config={'EMAIL': email, 'PASSWORD': password})
        self.device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=name,
            )
        
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=MIN_TIME_BETWEEN_UPDATES)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            async with timeout(10):
                current = await self.daikinskyport.update()
        except (
            RequestException,
        ) as error:
            raise UpdateFailed(error) from error
        _LOGGER.debug("Daikin Skyport data updated successfully")
        return
