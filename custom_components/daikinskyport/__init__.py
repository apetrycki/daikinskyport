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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DaikinSkyport as config entry."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info("Daikin Skyport Starting")

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
    await coordinator.async_refresh()

    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )


    entry.add_update_listener(async_reload_entry)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

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
        self.platforms = []
        self.unique_id = unique_id
        self.daikinskyport = DaikinSkyport(config={'EMAIL': email, 'PASSWORD': password}, session=session)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer=MANUFACTURER,
            name=name,
            )
        
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=MIN_TIME_BETWEEN_UPDATES)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            current = await self.daikinskyport.update()
        except (
            RequestException,
        ) as error:
            raise UpdateFailed(error) from error
        _LOGGER.debug("Daikin Skyport data updated successfully")
        return
