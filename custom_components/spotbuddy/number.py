"""Number platform for SpotBuddy."""

import logging

from homeassistant.components.number import NumberExtraStoredData, RestoreNumber
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import (
    DEFAULT_DURATION_HOURS,
    DOMAIN,
    ENTITY_KEY_DURATION_NUMBER,
    ICON_TIME,
    NUMBER,
)
from .coordinator import SpotBuddyCoordinator
from .entity import SpotBuddyEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices) -> None:
    """Set up the number platform."""
    coordinator: SpotBuddyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([SpotBuddyNumberDuration(entry, coordinator)])


# pylint: disable=abstract-method
class SpotBuddyNumberDuration(SpotBuddyEntity, RestoreNumber):
    """How many hours of power the task needs. The one always-required field."""

    _entity_key = ENTITY_KEY_DURATION_NUMBER
    _platform = NUMBER
    _attr_icon = ICON_TIME
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0.25
    _attr_native_max_value = 24.0
    _attr_native_step = 0.25
    _attr_native_unit_of_measurement = "h"

    async def async_set_native_value(self, value: float) -> None:
        """Set a new duration and re-plan."""
        self._attr_native_value = value
        self.coordinator.duration_hours = value
        self.async_write_ha_state()
        await self.coordinator.async_config_updated()

    async def async_added_to_hass(self) -> None:
        """Restore the previous value, or fall back to the default."""
        await super().async_added_to_hass()
        restored: NumberExtraStoredData | None = await self.async_get_last_number_data()
        if restored is not None and restored.native_value is not None:
            self._attr_native_value = restored.native_value
        else:
            self._attr_native_value = DEFAULT_DURATION_HOURS
        self.coordinator.duration_hours = self._attr_native_value
