"""Entité de base JOAL."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import JoalConfigEntry
from .const import DOMAIN


class JoalEntity(Entity):
    """Entité mise à jour en push par le client JOAL."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: JoalConfigEntry, key: str) -> None:
        self._entry = entry
        self._client = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="JOAL",
            configuration_url=self._client.ui_url,
        )

    @property
    def available(self) -> bool:
        return self._client.state.connected and bool(self._client.state.config)

    @property
    def _config(self) -> dict[str, Any]:
        return self._client.state.config

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._client.add_listener(self.async_write_ha_state))
