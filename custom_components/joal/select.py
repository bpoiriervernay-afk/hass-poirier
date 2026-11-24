"""Choix du client émulé."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JoalConfigEntry
from .entity import JoalEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JoalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([ClientSelect(entry)])


class ClientSelect(JoalEntity, SelectEntity):
    _attr_name = "Client de torrent"
    _attr_icon = "mdi:application-edit"

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "client")

    @property
    def options(self) -> list[str]:
        options = list(self._client.state.clients)
        current = self._config.get("client")
        if current and current not in options:
            options.append(current)
        return options

    @property
    def current_option(self) -> str | None:
        return self._config.get("client")

    async def async_select_option(self, option: str) -> None:
        await self._client.async_save_config(client=option)
