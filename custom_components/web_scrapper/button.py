from homeassistant.components.button import ButtonEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WebScraperUpdateButton(coordinator, entry)])


class WebScraperUpdateButton(ButtonEntity):
    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_name = f"{entry.data['name']} Force Update"
        self._attr_unique_id = f"{entry.entry_id}_force_update"

    async def async_press(self):
        await self.coordinator.async_request_refresh()
