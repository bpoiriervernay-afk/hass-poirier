import re
import time
import logging
from datetime import timedelta

from bs4 import BeautifulSoup
from lxml import html

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import *


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

    async def _async_update_data(self):
        try:
            session = async_get_clientsession(self.hass)
    
            async with session.get(self.entry.data[CONF_URL], timeout=15) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"HTTP {resp.status}")
                content = await resp.text()
    
            if self.entry.data[CONF_SELECTOR_TYPE] == "css":
                soup = BeautifulSoup(content, "html.parser")
                elements = soup.select(self.entry.data[CONF_SELECTOR])
                text = "\n".join(e.get_text(" ", strip=True) for e in elements)
            else:
                doc = html.fromstring(content)
                nodes = doc.xpath(self.entry.data[CONF_SELECTOR])
                text = "\n".join(
                    n if isinstance(n, str) else " ".join(n.itertext())
                    for n in nodes
                )
    
            regex = self.entry.data.get(CONF_REGEX)
            if regex:
                text = re.findall(regex, text)
    
            self.last_status = "OK"
            self.last_update = time.strftime("%Y-%m-%d %H:%M:%S")
            return text
    
        except Exception as err:
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
            "url": self.entry.data[CONF_URL],
            "selector": self.entry.data[CONF_SELECTOR],
            "selector_type": self.entry.data[CONF_SELECTOR_TYPE],
        }
