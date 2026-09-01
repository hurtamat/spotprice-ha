"""Time platform for SpotBuddy.

Replaces the 96-option select the upstream integration used for its completion
time; Home Assistant has had a native time entity since 2023.4.
"""

from __future__ import annotations

from datetime import time as dt_time
import logging

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_READY_BY,
    DOMAIN,
    ENTITY_KEY_READY_BY_TIME,
    ENTITY_KEY_UNAVAILABLE_FROM_TIME,
    ENTITY_KEY_UNAVAILABLE_TO_TIME,
    ICON_TIME,
    ICON_TIMER_OFF,
    TIME,
)
from .coordinator import SpotBuddyCoordinator
from .entity import SpotBuddyEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices) -> None:
    """Set up the time platform."""
    coordinator: SpotBuddyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            SpotBuddyTimeReadyBy(entry, coordinator),
            SpotBuddyTimeUnavailableFrom(entry, coordinator),
            SpotBuddyTimeUnavailableTo(entry, coordinator),
        ]
    )


# pylint: disable=abstract-method
class SpotBuddyTime(SpotBuddyEntity, TimeEntity, RestoreEntity):
    """Base time entity; its value survives a restart."""

    _platform = TIME
    _attr_icon = ICON_TIME
    _attr_entity_category = EntityCategory.CONFIG
    _default: str | None = None

    async def async_set_value(self, value: dt_time) -> None:
        """Set a new time and re-plan."""
        self._attr_native_value = value
        self._push_to_coordinator()
        self.async_write_ha_state()
        await self.coordinator.async_config_updated()

    async def async_added_to_hass(self) -> None:
        """Restore the previous value, or fall back to the default."""
        await super().async_added_to_hass()
        restored: State | None = await self.async_get_last_state()
        value = dt_util.parse_time(restored.state) if restored is not None else None
        if value is None and self._default is not None:
            value = dt_util.parse_time(self._default)
        self._attr_native_value = value
        self._push_to_coordinator()

    def _push_to_coordinator(self) -> None:
        """Copy this entity's value onto the coordinator."""
        raise NotImplementedError


class SpotBuddyTimeReadyBy(SpotBuddyTime):
    """The deadline the task must finish by. The window is the 24h before it."""

    _entity_key = ENTITY_KEY_READY_BY_TIME
    _default = DEFAULT_READY_BY

    def _push_to_coordinator(self) -> None:
        self.coordinator.ready_by = self._attr_native_value


class SpotBuddyTimeUnavailableFrom(SpotBuddyTime):
    """Start of the do-not-run window. Unset means no window."""

    _entity_key = ENTITY_KEY_UNAVAILABLE_FROM_TIME
    _attr_icon = ICON_TIMER_OFF

    def _push_to_coordinator(self) -> None:
        self.coordinator.unavailable_from = self._attr_native_value


class SpotBuddyTimeUnavailableTo(SpotBuddyTime):
    """End of the do-not-run window. May wrap past midnight."""

    _entity_key = ENTITY_KEY_UNAVAILABLE_TO_TIME
    _attr_icon = ICON_TIMER_OFF

    def _push_to_coordinator(self) -> None:
        self.coordinator.unavailable_to = self._attr_native_value
