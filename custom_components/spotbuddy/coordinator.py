"""Coordinator for SpotBuddy.

Holds the committed run plan fetched from the SpotBuddy backend and derives the
current relay state from it. All optimization happens server-side; this class is
deliberately thin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SpotBuddyApiClient, SpotBuddyApiError, SpotBuddyAuthError
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CONTROLLED_SWITCH,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    DEFAULT_DURATION_HOURS,
    DEFAULT_READY_BY,
    DOMAIN,
    PLAN_REFRESH_HOURS_UTC,
    PLAN_REFRESH_MINUTE,
    PRICE_LEVELS,
    STATUS_DISABLED,
    STATUS_NO_PLAN,
    STATUS_RUNNING,
    STATUS_UNAVAILABLE,
    STATUS_WAITING_FOR_PLAN,
    STATUS_WAITING_TO_START,
)
from .helpers.general import get_parameter

_LOGGER = logging.getLogger(__name__)


def _level_name(level: int | None) -> str | None:
    """Map the backend PriceColor int (0/1/2) onto a slug. None stays None."""
    if level is None or not 0 <= level < len(PRICE_LEVELS):
        return None
    return PRICE_LEVELS[level]


@dataclass
class ScheduledBlock:
    """One contiguous ON block, as returned by POST /api/schedule."""

    start_utc: datetime
    end_utc: datetime
    eur_per_mwh: float | None = None

    def contains(self, moment: datetime) -> bool:
        """Whether moment falls inside this block."""
        return self.start_utc <= moment < self.end_utc


@dataclass
class CurveSlot:
    """One delivery slot of the price curve, parsed for lookup by time."""

    start_utc: datetime
    end_utc: datetime
    eur_per_mwh: float | None = None
    level: str | None = None

    def contains(self, moment: datetime) -> bool:
        """Whether moment falls inside this slot. Half-open, as on the backend."""
        return self.start_utc <= moment < self.end_utc


@dataclass
class SpotBuddyPlan:
    """The committed plan for one device, plus the ambient price state."""

    zone_name: str | None = None
    scheduled: bool = False
    blocks: list[ScheduledBlock] = field(default_factory=list)
    # The raw curve, passed through to the price sensor's attribute for chart cards.
    curve: list[dict] = field(default_factory=list)
    slots: list[CurveSlot] = field(default_factory=list)
    fetched_at: datetime | None = None

    def slot_at(self, moment: datetime) -> CurveSlot | None:
        """The curve slot covering moment, if any."""
        return next((s for s in self.slots if s.contains(moment)), None)

    def block_at(self, moment: datetime) -> ScheduledBlock | None:
        """The block covering moment, if any."""
        return next((b for b in self.blocks if b.contains(moment)), None)

    def next_block(self, moment: datetime) -> ScheduledBlock | None:
        """The first block starting after moment, if any."""
        upcoming = sorted(
            (b for b in self.blocks if b.start_utc >= moment),
            key=lambda b: b.start_utc,
        )
        return upcoming[0] if upcoming else None


class SpotBuddyCoordinator(DataUpdateCoordinator[SpotBuddyPlan]):
    """Fetches the plan on a schedule and drives entity state off it."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Refreshes are event-driven (see the time listeners below), not polled.
            update_interval=None,
        )
        self.config_entry = config_entry
        self.platforms: list[str] = []
        self.listeners: list = []

        # Connection settings, from the config flow.
        self.base_url: str = str(get_parameter(config_entry, CONF_BASE_URL, "")).rstrip(
            "/"
        )
        self.latitude: float = float(
            get_parameter(config_entry, CONF_LATITUDE, hass.config.latitude)
        )
        self.longitude: float = float(
            get_parameter(config_entry, CONF_LONGITUDE, hass.config.longitude)
        )
        # Optional: an entity we drive directly, so the user needs no automation.
        self.controlled_switch: str | None = (
            get_parameter(config_entry, CONF_CONTROLLED_SWITCH, "") or None
        )
        self.client = SpotBuddyApiClient(
            async_get_clientsession(hass),
            self.base_url,
            get_parameter(config_entry, CONF_API_KEY, "") or None,
        )

        # Task settings, owned by the config entities and restored by them on
        # startup. These are the fields of one task in the schedule request.
        self.enabled: bool = True
        self.continuous_block: bool = False
        self.duration_hours: float = DEFAULT_DURATION_HOURS
        self.ready_by: time | None = dt_util.parse_time(DEFAULT_READY_BY)
        self.unavailable_from: time | None = None
        self.unavailable_to: time | None = None

        # Re-evaluate the relay on every 15-minute slot boundary.
        self.listeners.append(
            async_track_time_change(
                hass, self._async_tick, minute=[0, 15, 30, 45], second=0
            )
        )
        # Re-fetch the plan after midnight and after the day-ahead prices publish.
        self.listeners.append(
            async_track_time_change(
                hass,
                self._async_scheduled_refresh,
                hour=PLAN_REFRESH_HOURS_UTC,
                minute=PLAN_REFRESH_MINUTE,
                second=0,
            )
        )

    def unsubscribe_listeners(self) -> None:
        """Drop every time listener. Called on unload."""
        for unsub in self.listeners:
            unsub()
        self.listeners = []

    async def _async_update_data(self) -> SpotBuddyPlan:
        """Fetch the committed plan and the price curve from the backend."""
        try:
            body = await self.client.async_get_schedule(
                device_id=self.config_entry.entry_id,
                latitude=self.latitude,
                longitude=self.longitude,
                for_date=self._target_date(),
                duration_hours=self.duration_hours,
                ready_by=self.ready_by,
                continuous_block=self.continuous_block,
                unavailable_from=self.unavailable_from,
                unavailable_to=self.unavailable_to,
            )
        except SpotBuddyAuthError as err:
            # Sends the user to the reconfigure flow rather than retrying forever.
            raise ConfigEntryAuthFailed(str(err)) from err
        except SpotBuddyApiError as err:
            raise UpdateFailed(str(err)) from err

        return self._parse_plan(body)

    def _target_date(self) -> date:
        """The day to schedule for.

        The backend anchors the window on the deadline and looks back 24h, so
        once today's deadline has passed the interesting plan is tomorrow's.
        """
        now = dt_util.utcnow()
        today = now.date()
        if self.ready_by is not None and now.time() >= self.ready_by:
            return today + timedelta(days=1)
        return today

    def _parse_plan(self, body: dict) -> SpotBuddyPlan:
        """Map the response body onto a SpotBuddyPlan.

        One config entry drives one appliance, so it always sends one task and
        reads tasks[0] — the same single-task convention as the Shelly script.
        """
        tasks = body.get("tasks") or []
        task = tasks[0] if tasks else {}

        blocks = []
        for raw in task.get("blocks") or []:
            start = dt_util.parse_datetime(raw.get("start_utc") or "")
            end = dt_util.parse_datetime(raw.get("end_utc") or "")
            if start is None or end is None:
                _LOGGER.warning("Skipping block with unparsable times: %s", raw)
                continue
            blocks.append(
                ScheduledBlock(
                    start_utc=dt_util.as_utc(start),
                    end_utc=dt_util.as_utc(end),
                    eur_per_mwh=raw.get("eur_per_mwh"),
                )
            )

        curve = body.get("curve") or []

        slots = []
        for raw in curve:
            start = dt_util.parse_datetime(raw.get("start_utc") or "")
            end = dt_util.parse_datetime(raw.get("end_utc") or "")
            if start is None or end is None:
                continue
            slots.append(
                CurveSlot(
                    start_utc=dt_util.as_utc(start),
                    end_utc=dt_util.as_utc(end),
                    eur_per_mwh=raw.get("eur_per_mwh"),
                    level=_level_name(raw.get("level")),
                )
            )

        return SpotBuddyPlan(
            zone_name=body.get("zone_name"),
            scheduled=bool(task.get("scheduled")),
            blocks=sorted(blocks, key=lambda b: b.start_utc),
            curve=curve,
            slots=sorted(slots, key=lambda s: s.start_utc),
            fetched_at=dt_util.utcnow(),
        )

    async def _async_scheduled_refresh(self, date_time: datetime | None = None) -> None:
        """Time-triggered plan refresh."""
        await self.async_refresh()
        await self.async_apply_control()

    async def async_config_updated(self) -> None:
        """A config entity changed; the committed plan no longer matches it."""
        _LOGGER.debug("SpotBuddyCoordinator.async_config_updated")
        await self.async_request_refresh()
        # The refresh is debounced, but "Enabled off" must reach the relay now.
        await self.async_apply_control()

    async def _async_tick(self, date_time: datetime | None = None) -> None:
        """Push the new slot's state out to the entities and the controlled switch."""
        self.async_update_listeners()
        await self.async_apply_control()

    async def async_apply_control(self) -> None:
        """Drive the controlled entity, if the user picked one.

        Only called when the desired state differs from the entity's actual one,
        so a user who flips the switch by hand keeps it until the next boundary
        rather than fighting us every tick.
        """
        if self.controlled_switch is None:
            return

        state = self.hass.states.get(self.controlled_switch)
        if state is None:
            _LOGGER.warning(
                "Controlled entity %s does not exist; not switching",
                self.controlled_switch,
            )
            return

        desired = self.is_running
        if (state.state == STATE_ON) == desired:
            return

        domain = self.controlled_switch.split(".", 1)[0]
        _LOGGER.debug(
            "Turning %s %s", self.controlled_switch, "on" if desired else "off"
        )
        await self.hass.services.async_call(
            domain,
            SERVICE_TURN_ON if desired else SERVICE_TURN_OFF,
            {"entity_id": self.controlled_switch},
            blocking=False,
        )

    @property
    def current_price(self) -> float | None:
        """Price for the slot happening now.

        Read off the curve rather than anything computed at fetch time: the plan is
        fetched twice a day, so a fetch-time value is stale within the hour. The
        curve covers today and tomorrow, and the quarter-hourly tick re-reads it.
        """
        if self.data is None:
            return None
        slot = self.data.slot_at(dt_util.utcnow())
        return slot.eur_per_mwh if slot is not None else None

    @property
    def price_level(self) -> str | None:
        """Price colour for the slot happening now. Same reasoning as current_price."""
        if self.data is None:
            return None
        slot = self.data.slot_at(dt_util.utcnow())
        return slot.level if slot is not None else None

    @property
    def next_start(self) -> datetime | None:
        """When the appliance next switches on. None while nothing further is planned.

        While a block is running this is the *following* block, which is what a split
        (non-continuous) plan needs.
        """
        if not self.enabled or self.data is None:
            return None
        block = self.data.next_block(dt_util.utcnow())
        return block.start_utc if block is not None else None

    @property
    def next_end(self) -> datetime | None:
        """When the current run ends, or the next one would. None when nothing is planned."""
        if not self.enabled or self.data is None:
            return None
        now = dt_util.utcnow()
        block = self.data.block_at(now) or self.data.next_block(now)
        return block.end_utc if block is not None else None

    @property
    def is_running(self) -> bool:
        """Whether the appliance should be on right now."""
        if not self.enabled or self.data is None:
            return False
        return self.data.block_at(dt_util.utcnow()) is not None

    @property
    def status(self) -> str:
        """A coarse, language-independent state for automations."""
        if not self.enabled:
            return STATUS_DISABLED

        if not self.last_update_success:
            return STATUS_UNAVAILABLE

        plan = self.data
        if plan is None or plan.fetched_at is None:
            return STATUS_WAITING_FOR_PLAN

        now = dt_util.utcnow()
        if plan.block_at(now) is not None:
            return STATUS_RUNNING
        if plan.next_block(now) is not None:
            return STATUS_WAITING_TO_START
        return STATUS_NO_PLAN

    @property
    def plan_age(self) -> timedelta | None:
        """How long ago the plan was fetched."""
        if self.data is None or self.data.fetched_at is None:
            return None
        return dt_util.utcnow() - self.data.fetched_at
