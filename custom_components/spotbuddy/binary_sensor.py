"""Binary sensor platform for SpotBuddy."""

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant

from .const import BINARY_SENSOR, DOMAIN, ENTITY_KEY_RUNNING
from .coordinator import SpotBuddyCoordinator
from .entity import SpotBuddyCoordinatorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices) -> None:
    """Set up the binary sensor platform."""
    coordinator: SpotBuddyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([SpotBuddyBinarySensorRunning(entry, coordinator)])


class SpotBuddyBinarySensorRunning(SpotBuddyCoordinatorEntity, BinarySensorEntity):
    """On while the current time falls inside a committed run block.

    This is the whole contract for automations: wire it to any switch you own.
    """

    _entity_key = ENTITY_KEY_RUNNING
    _platform = BINARY_SENSOR

    @property
    def is_on(self) -> bool:
        """Whether the appliance should be running now."""
        return self.coordinator.is_running

    @property
    def extra_state_attributes(self) -> dict:
        """Enough context to render the plan without a second call."""
        plan = self.coordinator.data
        if plan is None:
            return {}

        blocks = [
            {
                "start_utc": block.start_utc.isoformat(),
                "end_utc": block.end_utc.isoformat(),
                "eur_per_mwh": block.eur_per_mwh,
            }
            for block in plan.blocks
        ]

        return {
            "zone_name": plan.zone_name,
            "scheduled": plan.scheduled,
            "blocks": blocks,
            "schedule": _as_step_series(plan.blocks),
        }


def _as_step_series(blocks) -> list[dict]:
    """The blocks as an on/off step series, which is what charting cards can draw."""
    series = []
    for block in blocks:
        series.append({"start": block.start_utc.isoformat(), "value": 1})
        series.append({"start": block.end_utc.isoformat(), "value": 0})
    return series
