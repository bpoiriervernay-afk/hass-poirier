import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import *

class WebScraperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_URL): str,
                vol.Required(CONF_SELECTOR): str,
                vol.Required(CONF_SELECTOR_TYPE, default="css"): vol.In(["css", "xpath"]),
                vol.Optional(CONF_REGEX): str,
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WebScraperOptionsFlow(config_entry)


class WebScraperOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): vol.Coerce(int)
            })
        )
