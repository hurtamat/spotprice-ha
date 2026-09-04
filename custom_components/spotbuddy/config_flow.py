"""Config flow for SpotBuddy."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CONTROLLED_SWITCH,
    CONF_DEVICE_NAME,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    DEFAULT_BASE_URL,
    DOMAIN,
)
from .helpers.general import DeviceNameCreator, get_parameter

_LOGGER = logging.getLogger(__name__)

# step="any" rather than a small float: Home Assistant rejects a step below 0.001,
# and coordinates want full precision anyway.
_COORDINATE_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=-180, max=180, step="any", mode=NumberSelectorMode.BOX)
)

# Leave empty to publish binary_sensor.spotbuddy_running only and automate it yourself.
_CONTROLLED_SWITCH_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["switch", "input_boolean"])
)


def _validate(user_input: dict[str, Any]) -> tuple[str, str] | None:
    """Return (field, error_key) for the first problem found, else None."""
    base_url = str(user_input.get(CONF_BASE_URL, "")).strip()
    if not base_url.startswith(("http://", "https://")):
        return (CONF_BASE_URL, "invalid_url")
    return None


class SpotBuddyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SpotBuddyOptionsFlow()

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        self._errors = {}

        if user_input is None:
            # Home Assistant already knows where the house is; default to that.
            user_input = {
                CONF_DEVICE_NAME: DeviceNameCreator.create(self.hass),
                CONF_BASE_URL: DEFAULT_BASE_URL,
                CONF_API_KEY: "",
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
                CONF_CONTROLLED_SWITCH: "",
            }
        else:
            error = _validate(user_input)
            if error is not None:
                self._errors[error[0]] = error[1]
            if not self._errors:
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_NAME, default=user_input[CONF_DEVICE_NAME]
                    ): TextSelector(),
                    vol.Required(
                        CONF_BASE_URL, default=user_input[CONF_BASE_URL]
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                    vol.Optional(
                        CONF_API_KEY, default=user_input[CONF_API_KEY]
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                    vol.Required(
                        CONF_LATITUDE, default=user_input[CONF_LATITUDE]
                    ): _COORDINATE_SELECTOR,
                    vol.Required(
                        CONF_LONGITUDE, default=user_input[CONF_LONGITUDE]
                    ): _COORDINATE_SELECTOR,
                    vol.Optional(
                        CONF_CONTROLLED_SWITCH,
                        description={
                            "suggested_value": user_input[CONF_CONTROLLED_SWITCH]
                        },
                    ): _CONTROLLED_SWITCH_SELECTOR,
                }
            ),
            errors=self._errors,
            last_step=True,
        )


class SpotBuddyOptionsFlow(config_entries.OptionsFlow):
    """Handle reconfiguration of an existing entry."""

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        self._errors = {}

        if user_input is not None:
            error = _validate(user_input)
            if error is not None:
                self._errors[error[0]] = error[1]
            if not self._errors:
                return self.async_create_entry(
                    title=self.config_entry.title, data=user_input
                )

        entry = self.config_entry
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BASE_URL,
                        default=get_parameter(entry, CONF_BASE_URL, DEFAULT_BASE_URL),
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                    vol.Optional(
                        CONF_API_KEY, default=get_parameter(entry, CONF_API_KEY, "")
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
                    vol.Required(
                        CONF_LATITUDE, default=get_parameter(entry, CONF_LATITUDE)
                    ): _COORDINATE_SELECTOR,
                    vol.Required(
                        CONF_LONGITUDE, default=get_parameter(entry, CONF_LONGITUDE)
                    ): _COORDINATE_SELECTOR,
                    vol.Optional(
                        CONF_CONTROLLED_SWITCH,
                        description={
                            "suggested_value": get_parameter(
                                entry, CONF_CONTROLLED_SWITCH, ""
                            )
                        },
                    ): _CONTROLLED_SWITCH_SELECTOR,
                }
            ),
            errors=self._errors,
            last_step=True,
        )
