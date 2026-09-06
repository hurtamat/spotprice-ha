"""Config flow for SpotBuddy."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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

from .api import SpotBuddyApiClient, SpotBuddyApiError
from .const import (
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


def _is_url(value: str) -> bool:
    """Whether a string is shaped like a backend URL."""
    return value.strip().startswith(("http://", "https://"))


class SpotBuddyFlowMixin:
    """Form building and validation shared by the config and options flows.

    The backend URL is a constant, not a question: the hosted backend is the same for
    everyone. It only becomes a field once a connection has failed and the user needs a
    way out, or when an entry already points somewhere custom.

    Home Assistant's Advanced Mode is deliberately not used as the trigger: it is on by
    default for admin users, and everyone setting up an integration is an admin, so it
    would show the field to everybody.
    """

    _errors: dict[str, str]
    # Set after a failed connection, so the URL field appears on the retry.
    _url_failed: bool = False

    def _url_visible(self, entry_url: str | None = None) -> bool:
        """Whether to render the backend URL field at all."""
        # An entry already pointing somewhere custom keeps its field, or the user could
        # never undo the override.
        overridden = entry_url is not None and entry_url != DEFAULT_BASE_URL
        visible = self._url_failed or overridden
        _LOGGER.debug(
            "URL field visible=%s (failed=%s, overridden=%s, entry_url=%r, default=%r)",
            visible,
            self._url_failed,
            overridden,
            entry_url,
            DEFAULT_BASE_URL,
        )
        return visible

    def _schema(self, defaults: dict[str, Any], *, with_name: bool) -> vol.Schema:
        """The form, with the URL field included only when it should be visible."""
        fields: dict[Any, Any] = {}

        if with_name:
            fields[vol.Required(CONF_DEVICE_NAME, default=defaults[CONF_DEVICE_NAME])] = (
                TextSelector()
            )

        if self._url_visible(defaults.get(CONF_BASE_URL)):
            fields[
                vol.Required(CONF_BASE_URL, default=defaults[CONF_BASE_URL])
            ] = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))

        fields[vol.Required(CONF_LATITUDE, default=defaults[CONF_LATITUDE])] = (
            _COORDINATE_SELECTOR
        )
        fields[vol.Required(CONF_LONGITUDE, default=defaults[CONF_LONGITUDE])] = (
            _COORDINATE_SELECTOR
        )
        fields[
            vol.Optional(
                CONF_CONTROLLED_SWITCH,
                description={"suggested_value": defaults[CONF_CONTROLLED_SWITCH]},
            )
        ] = _CONTROLLED_SWITCH_SELECTOR

        return vol.Schema(fields)

    async def _async_validate(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Check the input and that the backend answers. Fills self._errors.

        Returns the input with the effective backend URL filled in, since the field is
        absent from the form in the normal case.
        """
        self._errors = {}

        data = dict(user_input)
        data.setdefault(CONF_BASE_URL, DEFAULT_BASE_URL)

        if not _is_url(str(data[CONF_BASE_URL])):
            self._errors[CONF_BASE_URL] = "invalid_url"
            return data

        client = SpotBuddyApiClient(
            async_get_clientsession(self.hass), str(data[CONF_BASE_URL]), None
        )
        try:
            await client.async_check_connection(
                latitude=float(data[CONF_LATITUDE]),
                longitude=float(data[CONF_LONGITUDE]),
            )
        except SpotBuddyApiError as err:
            _LOGGER.debug("Backend unreachable during setup: %s", err)
            # Reveal the URL field on the retry, so a user with a self-hosted backend
            # or a typo in the constant can point us somewhere else.
            self._url_failed = True
            self._errors["base"] = "cannot_connect"

        return data


class SpotBuddyConfigFlow(SpotBuddyFlowMixin, config_entries.ConfigFlow, domain=DOMAIN):
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

        defaults = {
            CONF_DEVICE_NAME: DeviceNameCreator.create(self.hass),
            CONF_BASE_URL: DEFAULT_BASE_URL,
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
            CONF_CONTROLLED_SWITCH: "",
        }

        if user_input is not None:
            data = await self._async_validate(user_input)
            if not self._errors:
                return self.async_create_entry(
                    title=data[CONF_DEVICE_NAME], data=data
                )
            # Keep what the user typed, so a retry does not start over.
            defaults.update(data)

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(defaults, with_name=True),
            errors=self._errors,
            last_step=True,
        )


class SpotBuddyOptionsFlow(SpotBuddyFlowMixin, config_entries.OptionsFlow):
    """Handle reconfiguration of an existing entry."""

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        self._errors = {}
        entry = self.config_entry

        defaults = {
            CONF_BASE_URL: get_parameter(entry, CONF_BASE_URL, DEFAULT_BASE_URL),
            CONF_LATITUDE: get_parameter(entry, CONF_LATITUDE),
            CONF_LONGITUDE: get_parameter(entry, CONF_LONGITUDE),
            CONF_CONTROLLED_SWITCH: get_parameter(entry, CONF_CONTROLLED_SWITCH, ""),
        }

        if user_input is not None:
            # A form without the URL field must not silently reset a custom backend.
            merged = {CONF_BASE_URL: defaults[CONF_BASE_URL], **user_input}
            data = await self._async_validate(merged)
            if not self._errors:
                return self.async_create_entry(title=entry.title, data=data)
            defaults.update(data)

        return self.async_show_form(
            step_id="init",
            data_schema=self._schema(defaults, with_name=False),
            errors=self._errors,
            last_step=True,
        )
