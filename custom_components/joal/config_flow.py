"""Flux de configuration de l'intégration JOAL."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from yarl import URL

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PORT, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import JoalAuthError, JoalClient, JoalError, normalize_url
from .const import CONF_PATH_PREFIX, CONF_SECRET_TOKEN, DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_PORT): cv.port,
        vol.Required(CONF_PATH_PREFIX): str,
        vol.Required(CONF_SECRET_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class JoalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ajout de JOAL depuis l'interface."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_URL] = normalize_url(user_input[CONF_URL])
            except ValueError:
                errors[CONF_URL] = "invalid_url"
            else:
                self._async_abort_entries_match(
                    {CONF_URL: user_input[CONF_URL], CONF_PORT: user_input[CONF_PORT]}
                )
                client = JoalClient.from_data(async_get_clientsession(self.hass), user_input)
                try:
                    await client.connect()
                except JoalAuthError:
                    errors["base"] = "invalid_auth"
                except JoalError:
                    errors["base"] = "cannot_connect"
                else:
                    host = URL(user_input[CONF_URL]).host
                    return self.async_create_entry(title=f"JOAL ({host})", data=user_input)
                finally:
                    await client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input),
            errors=errors,
        )
