"""The SpotBuddy integration."""

import asyncio
import logging

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry, DeviceRegistry
from homeassistant.helpers.device_registry import async_get as async_device_registry_get
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
    async_entries_for_config_entry,
)
from homeassistant.helpers.entity_registry import async_get as async_entity_registry_get
from homeassistant.helpers.start import async_at_started

from .const import (
    CARD_SOURCE_PATH,
    CARD_URL,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
    VERSION,
)
from .coordinator import SpotBuddyCoordinator

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the bundled Lovelace card, once per Home Assistant start."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(CARD_URL, hass.config.path(CARD_SOURCE_PATH), True)
        ]
    )
    # The version query busts the browser cache on update.
    frontend.add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    _LOGGER.debug("Registered %s", CARD_URL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SpotBuddy from a config entry."""
    _LOGGER.debug("async_setup_entry")

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    coordinator = SpotBuddyCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    coordinator.platforms.extend(PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # The config entities restore their values as they are added, so the first
    # fetch happens once the platforms are up rather than before them.
    await coordinator.async_refresh()

    # The controlled switch may not exist yet during a cold start. Fires at once if HA is up.
    async def _apply_when_started(_hass: HomeAssistant) -> None:
        await coordinator.async_apply_control()

    entry.async_on_unload(async_at_started(hass, _apply_when_started))

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    _sync_device_name(hass, entry)
    return True


def _sync_device_name(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Keep the device name in step with a renamed config entry."""
    entity_registry: EntityRegistry = async_entity_registry_get(hass)
    all_entities = async_entries_for_config_entry(entity_registry, entry.entry_id)
    if not all_entities:
        return

    device_registry: DeviceRegistry = async_device_registry_get(hass)
    device: DeviceEntry | None = device_registry.async_get(all_entities[0].device_id)
    if device is None:
        return

    current = device.name_by_user if device.name_by_user is not None else device.name
    if entry.title != current:
        device_registry.async_update_device(device.id, name_by_user=entry.title)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug("async_unload_entry")
    coordinator: SpotBuddyCoordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, coordinator.platforms
    )
    if unloaded:
        coordinator.unsubscribe_listeners()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


# Serialises reload so a setup always completes before the next unload starts.
_reload_lock = asyncio.Lock()


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("async_reload_entry")
    async with _reload_lock:
        await async_unload_entry(hass, entry)
        await async_setup_entry(hass, entry)
