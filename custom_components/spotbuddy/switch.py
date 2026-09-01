"""Switch platform for SpotBuddy."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    ENTITY_KEY_CONTINUOUS_SWITCH,
    ENTITY_KEY_ENABLED_SWITCH,
    SWITCH,
)
from .coordinator import SpotBuddyCoordinator
from .entity import SpotBuddyEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices) -> None:
    """Set up the switch platform."""
    coordinator: SpotBuddyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            SpotBuddySwitchEnabled(entry, coordinator),
            SpotBuddySwitchContinuous(entry, coordinator),
        ]
    )


# pylint: disable=abstract-method
class SpotBuddySwitch(SpotBuddyEntity, SwitchEntity, RestoreEntity):
    """Base switch; its state survives a restart."""

    _platform = SWITCH
    _default_on = True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = True
        await self._async_apply()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self._attr_is_on = False
        await self._async_apply()

    async def async_added_to_hass(self) -> None:
        """Restore the previous state, or fall back to the default."""
        await super().async_added_to_hass()
        restored: State | None = await self.async_get_last_state()
        self._attr_is_on = (
            restored.state == STATE_ON if restored is not None else self._default_on
        )
        self._push_to_coordinator()

    async def _async_apply(self) -> None:
        """Push the new value to the coordinator and re-plan."""
        self._push_to_coordinator()
        self.async_write_ha_state()
        await self.coordinator.async_config_updated()

    def _push_to_coordinator(self) -> None:
        """Copy this entity's value onto the coordinator."""
        raise NotImplementedError


class SpotBuddySwitchEnabled(SpotBuddySwitch):
    """Master switch. Off means the run block sensor stays off."""

    _entity_key = ENTITY_KEY_ENABLED_SWITCH
    _default_on = True

    def _push_to_coordinator(self) -> None:
        self.coordinator.enabled = bool(self.is_on)


class SpotBuddySwitchContinuous(SpotBuddySwitch):
    """Whether the hours must run back to back."""

    _entity_key = ENTITY_KEY_CONTINUOUS_SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _default_on = False

    def _push_to_coordinator(self) -> None:
        self.coordinator.continuous_block = bool(self.is_on)
