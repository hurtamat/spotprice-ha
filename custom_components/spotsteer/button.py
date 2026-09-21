"""Button platform for SpotSteer."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant

from .const import BUTTON, DOMAIN, ENTITY_KEY_REFRESH_BUTTON, ICON_REFRESH
from .coordinator import SpotSteerCoordinator
from .entity import SpotSteerEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices) -> None:
    """Set up the button platform."""
    coordinator: SpotSteerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([SpotSteerButtonRefresh(entry, coordinator)])


class SpotSteerButtonRefresh(SpotSteerEntity, ButtonEntity):
    """Fetch the plan again now, rather than waiting for the next refresh."""

    _entity_key = ENTITY_KEY_REFRESH_BUTTON
    _platform = BUTTON
    _attr_icon = ICON_REFRESH

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()
