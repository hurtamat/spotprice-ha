"""Client for the SpotBuddy backend."""

from __future__ import annotations

import asyncio
from datetime import date as dt_date, time as dt_time
import logging
from typing import Any

import aiohttp

from .const import API_TIMEOUT_SECONDS, SCHEDULE_PATH

_LOGGER = logging.getLogger(__name__)


class SpotBuddyApiError(Exception):
    """Raised when the backend cannot be reached or answers with an error."""


class SpotBuddyAuthError(SpotBuddyApiError):
    """Raised when the backend rejects the API key."""


class SpotBuddyApiClient:
    """Thin wrapper over POST /api/homeassistant/schedule.

    One call per refresh: the response carries the committed plan and the price
    curve together.
    """

    def __init__(
        self, session: aiohttp.ClientSession, base_url: str, api_key: str | None
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def async_get_schedule(
        self,
        *,
        device_id: str,
        latitude: float,
        longitude: float,
        for_date: dt_date,
        duration_hours: float,
        ready_by: dt_time | None,
        continuous_block: bool,
        unavailable_from: dt_time | None = None,
        unavailable_to: dt_time | None = None,
    ) -> dict[str, Any]:
        """Ask the backend for this device's plan. Returns the parsed body."""
        payload: dict[str, Any] = {
            "device_id": device_id,
            "lat": latitude,
            "lon": longitude,
            "date": for_date.isoformat(),
            "tasks": [
                {
                    "task_id": 1,
                    "duration_hours": duration_hours,
                    "ready_by": ready_by.isoformat() if ready_by else None,
                    "continuous_block": continuous_block,
                }
            ],
        }

        # The window is optional and only meaningful with both ends set.
        if unavailable_from is not None and unavailable_to is not None:
            payload["unavailable"] = {
                "from": unavailable_from.isoformat(),
                "to": unavailable_to.isoformat(),
            }

        return await self._async_post(SCHEDULE_PATH, payload)

    async def _async_post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON and return the parsed body, or raise SpotBuddyApiError."""
        url = f"{self._base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-Api-Key"] = self._api_key

        try:
            async with asyncio.timeout(API_TIMEOUT_SECONDS):
                response = await self._session.post(url, json=payload, headers=headers)

                if response.status in (401, 403):
                    raise SpotBuddyAuthError(
                        f"Backend rejected the API key ({response.status})"
                    )
                if response.status >= 400:
                    body = await response.text()
                    raise SpotBuddyApiError(
                        f"{url} returned {response.status}: {body[:200]}"
                    )

                return await response.json()

        except TimeoutError as err:
            raise SpotBuddyApiError(f"Timeout calling {url}") from err
        except aiohttp.ClientError as err:
            raise SpotBuddyApiError(f"Cannot reach {url}: {err}") from err
