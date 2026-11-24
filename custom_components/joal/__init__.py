"""Intégration Home Assistant pour JOAL."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JoalAuthError, JoalClient, JoalError

PLATFORMS = [Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

type JoalConfigEntry = ConfigEntry[JoalClient]


async def async_setup_entry(hass: HomeAssistant, entry: JoalConfigEntry) -> bool:
    client = JoalClient.from_data(async_get_clientsession(hass), entry.data)
    try:
        await client.connect()
    except JoalAuthError as err:
        raise ConfigEntryError(f"Secret token refusé par JOAL : {err}") from err
    except JoalError as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.async_create_background_task(hass, client.run(), "joal_stomp")
    if not await client.wait_ready(15):
        await client.close()
        raise ConfigEntryNotReady("JOAL n'a pas envoyé sa configuration")

    entry.runtime_data = client
    entry.async_on_unload(client.close)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JoalConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
