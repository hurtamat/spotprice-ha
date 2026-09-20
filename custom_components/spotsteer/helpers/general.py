"""General helpers."""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceRegistry
from homeassistant.helpers.device_registry import async_entries_for_config_entry
from homeassistant.helpers.device_registry import async_get as async_device_registry_get

from ..const import DOMAIN, NAME

_LOGGER = logging.getLogger(__name__)


def get_parameter(config_entry: ConfigEntry, parameter: str, default_val: Any = None):
    """Get a parameter from the OptionsFlow, falling back to the ConfigFlow."""
    if parameter in config_entry.options:
        return config_entry.options.get(parameter)
    if parameter in config_entry.data:
        return config_entry.data.get(parameter)
    return default_val


class DeviceNameCreator:
    """Creates the name of a newly added device."""

    @staticmethod
    def create(hass: HomeAssistant) -> str:
        """Return NAME, or NAME with the next free number appended."""
        # Our own entries, not the whole registry: `devices` as a mapping is deprecated.
        device_registry: DeviceRegistry = async_device_registry_get(hass)
        our_devices = []
        for entry in hass.config_entries.async_entries(DOMAIN):
            our_devices.extend(
                async_entries_for_config_entry(device_registry, entry.entry_id)
            )

        if not our_devices:
            return NAME

        highest = 1
        for device in our_devices:
            if device.name == NAME:
                continue
            try:
                number = int(device.name[len(NAME) :])
            except (ValueError, TypeError):
                continue
            highest = max(highest, number)
        return f"{NAME} {highest + 1}"
