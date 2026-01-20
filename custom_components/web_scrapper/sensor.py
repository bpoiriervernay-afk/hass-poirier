import time
import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import *
from .scraper import async_fetch_and_extract, WebScraperRequestError


class WebScraperCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.entry = entry
        self.last_status = "Init"
        self.last_update = None
        self.logger = logging.getLogger(__name__)

        super().__init__(
            hass,
            logger=self.logger,
            name="WebScraper",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    def _get_config(self, key, default=None):
        if key in self.entry.options:
            return self.entry.options.get(key)
        return self.entry.data.get(key, default)

    async def _async_update_data(self):
        try:
            text = await async_fetch_and_extract(
                self.hass,
                url=self._get_config(CONF_URL),
                selector=self._get_config(CONF_SELECTOR),
                selector_type=self._get_config(CONF_SELECTOR_TYPE),
                regex=self._get_config(CONF_REGEX),
                request_method=self._get_config(
                    CONF_REQUEST_METHOD, DEFAULT_REQUEST_METHOD
                ),
            )

            self.last_status = "OK"
            self.last_update = time.strftime("%Y-%m-%d %H:%M:%S")
            return text
    
        except WebScraperRequestError as err:
            self.last_status = "Erreur"
            raise UpdateFailed(str(err))


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WebScraperSensor(coordinator, entry)])


class WebScraperSensor(SensorEntity):
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = entry.data[CONF_NAME]
        self._attr_unique_id = f"web_scraper_{entry.entry_id}"

    @property
    def native_value(self):
        return self.coordinator.data

    @property
    def extra_state_attributes(self):
        return {
            "status": self.coordinator.last_status,
            "last_update": self.coordinator.last_update,
            "scan_interval_sec": self.coordinator.update_interval.total_seconds(),
            "url": self.coordinator._get_config(CONF_URL),
            "selector": self.coordinator._get_config(CONF_SELECTOR),
            "selector_type": self.coordinator._get_config(CONF_SELECTOR_TYPE),
            "request_method": self.coordinator._get_config(
                CONF_REQUEST_METHOD, DEFAULT_REQUEST_METHOD
            ),
        }
