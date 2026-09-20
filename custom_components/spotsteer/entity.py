"""Base entity classes for SpotSteer."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ICON, NAME, VERSION
from .coordinator import SpotSteerCoordinator

_LOGGER = logging.getLogger(__name__)


class SpotSteerEntityBase:
    """Shared identity for every SpotSteer entity.

    Entity ids are derived by Home Assistant from the device name and the
    translation key; we deliberately do not assign entity_id ourselves.
    """

    _attr_icon = ICON
    _attr_has_entity_name = True

    _entity_key: str
    _platform: str

    def _init_identity(self, entry: ConfigEntry) -> None:
        self.config_entry = entry
        self._attr_translation_key = self._entity_key
        self._attr_unique_id = f"{entry.entry_id}_{self._platform}_{self._entity_key}"

    @property
    def device_info(self):
        """Group every entity under one device per config entry."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": self.config_entry.title,
            "model": VERSION,
            "manufacturer": NAME,
        }


class SpotSteerEntity(SpotSteerEntityBase, Entity):
    """A user-settable entity. Its value is restored, not fetched."""

    def __init__(self, entry: ConfigEntry, coordinator: SpotSteerCoordinator) -> None:
        self.coordinator = coordinator
        self._init_identity(entry)


class SpotSteerCoordinatorEntity(
    SpotSteerEntityBase, CoordinatorEntity[SpotSteerCoordinator]
):
    """A read-only entity whose value comes from the coordinator."""

    def __init__(self, entry: ConfigEntry, coordinator: SpotSteerCoordinator) -> None:
        super().__init__(coordinator)
        self._init_identity(entry)
