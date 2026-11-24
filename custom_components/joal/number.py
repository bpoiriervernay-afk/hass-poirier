"""Paramètres numériques JOAL."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JoalConfigEntry
from .const import DEFAULT_RATIO, OPT_RATIO
from .entity import JoalEntity


@dataclass(frozen=True, kw_only=True)
class JoalNumberDescription(NumberEntityDescription):
    config_key: str


NUMBERS = (
    JoalNumberDescription(
        key="min_upload_rate",
        name="Taux d'upload minimum",
        config_key="minUploadRate",
        native_min_value=1,
        native_max_value=10000,
        native_step=1,
        native_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        mode=NumberMode.BOX,
        icon="mdi:speedometer-slow",
    ),
    JoalNumberDescription(
        key="max_upload_rate",
        name="Taux d'upload maximum",
        config_key="maxUploadRate",
        native_min_value=1,
        native_max_value=10000,
        native_step=1,
        native_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        mode=NumberMode.BOX,
        icon="mdi:speedometer",
    ),
    JoalNumberDescription(
        key="simultaneous_seed",
        name="Uploads simultanés",
        config_key="simultaneousSeed",
        native_min_value=1,
        native_max_value=500,
        native_step=1,
        mode=NumberMode.BOX,
        icon="mdi:format-list-numbered",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JoalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [*(JoalConfigNumber(entry, d) for d in NUMBERS), RatioTargetNumber(entry)]
    )


class JoalConfigNumber(JoalEntity, NumberEntity):
    entity_description: JoalNumberDescription

    def __init__(self, entry: JoalConfigEntry, description: JoalNumberDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self._config.get(self.entity_description.config_key)

    async def async_set_native_value(self, value: float) -> None:
        key = self.entity_description.config_key
        if key == "minUploadRate" and value > self._config.get("maxUploadRate", value):
            raise HomeAssistantError("Le minimum ne peut pas dépasser le maximum")
        if key == "maxUploadRate" and value < self._config.get("minUploadRate", value):
            raise HomeAssistantError("Le maximum ne peut pas être inférieur au minimum")
        await self._client.async_save_config(**{key: int(value)})


class RatioTargetNumber(JoalEntity, NumberEntity):
    """Ratio souhaité, mémorisé même quand le ratio cible est désactivé."""

    _attr_name = "Taux souhaité"
    _attr_icon = "mdi:scale-balance"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 10.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "ratio_value")

    @property
    def native_value(self) -> float:
        current = self._config.get("uploadRatioTarget", -1)
        if current >= 0:
            return current
        return self._entry.options.get(OPT_RATIO, DEFAULT_RATIO)

    async def async_set_native_value(self, value: float) -> None:
        value = round(value, 2)
        self.hass.config_entries.async_update_entry(
            self._entry, options={**self._entry.options, OPT_RATIO: value}
        )
        if self._config.get("uploadRatioTarget", -1) >= 0:
            await self._client.async_save_config(uploadRatioTarget=value)
        else:
            self.async_write_ha_state()
