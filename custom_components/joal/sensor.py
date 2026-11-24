"""Capteurs JOAL."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JoalConfigEntry
from .entity import JoalEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JoalConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        [TorrentCountSensor(entry), UploadSpeedSensor(entry), ActiveClientSensor(entry)]
    )


class TorrentCountSensor(JoalEntity, SensorEntity):
    _attr_name = "Nombre de torrents"
    _attr_icon = "mdi:file-multiple"
    _attr_native_unit_of_measurement = "torrents"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "torrent_count")

    @property
    def native_value(self) -> int:
        return len(self._client.state.torrents)


class UploadSpeedSensor(JoalEntity, SensorEntity):
    _attr_name = "Vitesse d'émission"
    _attr_device_class = SensorDeviceClass.DATA_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfDataRate.BYTES_PER_SECOND
    _attr_suggested_unit_of_measurement = UnitOfDataRate.KILOBYTES_PER_SECOND
    _attr_suggested_display_precision = 1

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "upload_speed")

    @property
    def native_value(self) -> float:
        return self._client.state.upload_speed


class ActiveClientSensor(JoalEntity, SensorEntity):
    """Client réellement émulé (ou celui configuré si le seed est arrêté)."""

    _attr_name = "Client actif"
    _attr_icon = "mdi:application-cog"

    def __init__(self, entry: JoalConfigEntry) -> None:
        super().__init__(entry, "active_client")

    @property
    def native_value(self) -> str | None:
        state = self._client.state
        if state.seeding and state.active_client:
            return state.active_client
        client = self._config.get("client")
        return client.removesuffix(".client") if client else None
