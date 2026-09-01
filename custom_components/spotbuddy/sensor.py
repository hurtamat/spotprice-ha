"""Sensor platform for SpotBuddy."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    ENTITY_KEY_PRICE,
    ENTITY_KEY_PRICE_LEVEL,
    ENTITY_KEY_STATUS,
    ICON_CASH,
    PRICE_LEVELS,
    SENSOR,
    STATUS_DISABLED,
    STATUS_NO_PLAN,
    STATUS_RUNNING,
    STATUS_UNAVAILABLE,
    STATUS_WAITING_FOR_PLAN,
    STATUS_WAITING_TO_START,
)
from .coordinator import SpotBuddyCoordinator
from .entity import SpotBuddyCoordinatorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_devices) -> None:
    """Set up the sensor platform."""
    coordinator: SpotBuddyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            SpotBuddySensorStatus(entry, coordinator),
            SpotBuddySensorPrice(entry, coordinator),
            SpotBuddySensorPriceLevel(entry, coordinator),
        ]
    )


class SpotBuddySensor(SpotBuddyCoordinatorEntity, SensorEntity):
    """Base sensor."""

    _platform = SENSOR


class SpotBuddySensorStatus(SpotBuddySensor):
    """What the integration is currently doing."""

    _entity_key = ENTITY_KEY_STATUS
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        STATUS_DISABLED,
        STATUS_WAITING_FOR_PLAN,
        STATUS_NO_PLAN,
        STATUS_WAITING_TO_START,
        STATUS_RUNNING,
        STATUS_UNAVAILABLE,
    ]

    @property
    def native_value(self) -> str:
        """The status slug."""
        return self.coordinator.status


class SpotBuddySensorPrice(SpotBuddySensor):
    """The spot price for the current slot."""

    _entity_key = ENTITY_KEY_PRICE
    _attr_icon = ICON_CASH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "EUR/MWh"
    # The curve is ~200 points and changes every slot; keep it out of the recorder
    # database, or every state write would store the whole array again.
    _unrecorded_attributes = frozenset(["curve"])

    @property
    def native_value(self) -> float | None:
        """Current price, or None when no plan has been fetched."""
        plan = self.coordinator.data
        return plan.current_price if plan is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        """The full curve, for chart cards and price-aware automations."""
        plan = self.coordinator.data
        if plan is None:
            return {}
        return {"zone_name": plan.zone_name, "curve": plan.curve}


class SpotBuddySensorPriceLevel(SpotBuddySensor):
    """The price colour for the current slot: green, yellow or red."""

    _entity_key = ENTITY_KEY_PRICE_LEVEL
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PRICE_LEVELS

    @property
    def native_value(self) -> str | None:
        """Colour slug, or None when the slot is unclassified."""
        plan = self.coordinator.data
        return plan.price_level if plan is not None else None
