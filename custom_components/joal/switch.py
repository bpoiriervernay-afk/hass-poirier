"""Interrupteurs JOAL."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JoalConfigEntry
from .const import DEFAULT_RATIO, OPT_RATIO
from .entity import JoalEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JoalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [RatioTargetSwitch(entry), KeepZeroLeechersSwitch(entry), SeedSwitch(entry)]
    )


class RatioTargetSwitch(JoalEntity, SwitchEntity):
    """Activé : uploadRatioTarget = taux souhaité ; désactivé : -1."""

    _attr_name = "Ratio cible"
    _attr_icon = "mdi:target"

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "ratio_enabled")

    @property
    def is_on(self) -> bool:
        return self._config.get("uploadRatioTarget", -1) >= 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        ratio = self._entry.options.get(OPT_RATIO, DEFAULT_RATIO)
        await self._client.async_save_config(uploadRatioTarget=float(ratio))

    async def async_turn_off(self, **kwargs: Any) -> None:
        current = self._config.get("uploadRatioTarget", -1)
        if current >= 0:  # mémorise la valeur pour la prochaine activation
            self.hass.config_entries.async_update_entry(
                self._entry, options={**self._entry.options, OPT_RATIO: current}
            )
        await self._client.async_save_config(uploadRatioTarget=-1.0)


class KeepZeroLeechersSwitch(JoalEntity, SwitchEntity):
    _attr_name = "Garder les torrents sans peers"
    _attr_icon = "mdi:account-off"

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "keep_zero_leechers")

    @property
    def is_on(self) -> bool:
        return bool(self._config.get("keepTorrentWithZeroLeechers"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.async_save_config(keepTorrentWithZeroLeechers=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.async_save_config(keepTorrentWithZeroLeechers=False)


class SeedSwitch(JoalEntity, SwitchEntity):
    _attr_name = "Seed actif"
    _attr_icon = "mdi:play-pause"

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "seeding")

    @property
    def is_on(self) -> bool:
        return self._client.state.seeding

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._client.async_start()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.async_stop()
