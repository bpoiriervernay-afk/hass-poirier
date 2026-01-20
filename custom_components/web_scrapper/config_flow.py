import voluptuous as vol
from homeassistant import config_entries

from .const import *
from .scraper import async_fetch_and_extract, WebScraperRequestError

CONF_TEST = "test_request"
DEFAULT_TEST_RESULT = "Aucun test"


def _normalize_user_input(user_input):
    data = dict(user_input)
    data.pop(CONF_TEST, None)
    if not data.get(CONF_REGEX):
        data.pop(CONF_REGEX, None)
    return data


def _format_test_result(result, limit=200):
    if isinstance(result, list):
        if not result:
            return ""
        text = ", ".join(str(x) for x in result)
    elif result is None:
        return ""
    else:
        text = str(result)

    if len(text) > limit:
        return f"{text[:limit]}..."
    return text


async def _async_run_test(hass, user_input):
    result = await async_fetch_and_extract(
        hass,
        url=user_input[CONF_URL],
        selector=user_input[CONF_SELECTOR],
        selector_type=user_input[CONF_SELECTOR_TYPE],
        regex=user_input.get(CONF_REGEX) or None,
        request_method=user_input.get(CONF_REQUEST_METHOD, DEFAULT_REQUEST_METHOD),
    )
    return _format_test_result(result)


class WebScraperConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._last_test_result = DEFAULT_TEST_RESULT

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            if user_input.get(CONF_TEST):
                try:
                    test_result = await _async_run_test(self.hass, user_input)
                    if not test_result:
                        errors["base"] = "empty_response"
                    self._last_test_result = test_result or DEFAULT_TEST_RESULT
                except WebScraperRequestError:
                    errors["base"] = "request_failed"
                    self._last_test_result = DEFAULT_TEST_RESULT
            else:
                data = _normalize_user_input(user_input)
                return self.async_create_entry(
                    title=data[CONF_NAME],
                    data=data,
                )

        defaults = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=defaults.get(CONF_NAME, "")
                    ): str,
                    vol.Required(
                        CONF_URL, default=defaults.get(CONF_URL, "")
                    ): str,
                    vol.Required(
                        CONF_SELECTOR, default=defaults.get(CONF_SELECTOR, "")
                    ): str,
                    vol.Required(
                        CONF_SELECTOR_TYPE,
                        default=defaults.get(CONF_SELECTOR_TYPE, "css"),
                    ): vol.In(["css", "xpath"]),
                    vol.Optional(
                        CONF_REGEX,
                        default=defaults.get(CONF_REGEX, ""),
                    ): str,
                    vol.Required(
                        CONF_REQUEST_METHOD,
                        default=defaults.get(
                            CONF_REQUEST_METHOD, DEFAULT_REQUEST_METHOD
                        ),
                    ): vol.In(["GET", "POST"]),
                    vol.Optional(CONF_TEST, default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"test_result": self._last_test_result},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return WebScraperOptionsFlow(config_entry)


class WebScraperOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry
        self._last_test_result = DEFAULT_TEST_RESULT

    def _get_default(self, key, fallback=None):
        if key in self.entry.options:
            return self.entry.options.get(key)
        return self.entry.data.get(key, fallback)

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            if user_input.get(CONF_TEST):
                try:
                    test_result = await _async_run_test(self.hass, user_input)
                    if not test_result:
                        errors["base"] = "empty_response"
                    self._last_test_result = test_result or DEFAULT_TEST_RESULT
                except WebScraperRequestError:
                    errors["base"] = "request_failed"
                    self._last_test_result = DEFAULT_TEST_RESULT
            else:
                data = _normalize_user_input(user_input)
                return self.async_create_entry(title="", data=data)

        defaults = {
            CONF_URL: self._get_default(CONF_URL, ""),
            CONF_SELECTOR: self._get_default(CONF_SELECTOR, ""),
            CONF_SELECTOR_TYPE: self._get_default(CONF_SELECTOR_TYPE, "css"),
            CONF_REGEX: self._get_default(CONF_REGEX, ""),
            CONF_REQUEST_METHOD: self._get_default(
                CONF_REQUEST_METHOD, DEFAULT_REQUEST_METHOD
            ),
        }
        if user_input:
            defaults.update(
                {
                    CONF_URL: user_input.get(CONF_URL, defaults[CONF_URL]),
                    CONF_SELECTOR: user_input.get(CONF_SELECTOR, defaults[CONF_SELECTOR]),
                    CONF_SELECTOR_TYPE: user_input.get(
                        CONF_SELECTOR_TYPE, defaults[CONF_SELECTOR_TYPE]
                    ),
                    CONF_REGEX: user_input.get(CONF_REGEX, defaults[CONF_REGEX]),
                    CONF_REQUEST_METHOD: user_input.get(
                        CONF_REQUEST_METHOD, defaults[CONF_REQUEST_METHOD]
                    ),
                }
            )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default=defaults[CONF_URL]): str,
                    vol.Required(
                        CONF_SELECTOR, default=defaults[CONF_SELECTOR]
                    ): str,
                    vol.Required(
                        CONF_SELECTOR_TYPE,
                        default=defaults[CONF_SELECTOR_TYPE],
                    ): vol.In(["css", "xpath"]),
                    vol.Optional(CONF_REGEX, default=defaults[CONF_REGEX]): str,
                    vol.Required(
                        CONF_REQUEST_METHOD,
                        default=defaults[CONF_REQUEST_METHOD],
                    ): vol.In(["GET", "POST"]),
                    vol.Optional(CONF_TEST, default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={"test_result": self._last_test_result},
        )
