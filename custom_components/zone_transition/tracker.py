"""Zone history tracking for a single person."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.const import STATE_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, EVENT_ZONE_TRANSITION, STORAGE_VERSION, signal_updated

ZONE_HOME = "zone.home"


def _parse_dt(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _format_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class ZoneTracker:
    """Remembers the zones a person has been in and fires transition events.

    Passing through "not_home" is ignored, so home -> not_home -> work is
    reported as a single home -> work transition.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str, person_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.person_id = person_id
        self.device_id: str | None = None

        self.current_zone: str | None = None
        self.arrived_at: datetime | None = None
        self.last_left_zone: str | None = None
        self.left_at: datetime | None = None
        self.previous_zone: str | None = None

        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}"
        )

    @property
    def last_known_zone(self) -> str | None:
        """The zone the person is in, or the last one they were in."""
        return self.current_zone or self.last_left_zone

    def zone_name(self, zone_id: str | None) -> str | None:
        """Friendly name of a zone entity, falling back to its entity id."""
        if zone_id is None:
            return None
        state = self.hass.states.get(zone_id)
        return state.name if state else zone_id

    async def async_start(self) -> None:
        """Restore saved history, sync with the current state and start listening."""
        data = await self._store.async_load() or {}
        self.current_zone = data.get("current_zone")
        self.arrived_at = _parse_dt(data.get("arrived_at"))
        self.last_left_zone = data.get("last_left_zone")
        self.left_at = _parse_dt(data.get("left_at"))
        self.previous_zone = data.get("previous_zone")

        # Catch up on anything that happened while we were not running.
        if (state := self.hass.states.get(self.person_id)) is not None:
            self._process(state)

    @callback
    def async_listen(self) -> Any:
        """Subscribe to person state changes; returns the unsubscribe callback."""

        @callback
        def _state_changed(event: Event[EventStateChangedData]) -> None:
            if (new_state := event.data["new_state"]) is not None:
                self._process(new_state)

        return async_track_state_change_event(
            self.hass, [self.person_id], _state_changed
        )

    def _resolve_zone(self, person_state: str) -> str | None:
        """Map a person's state ("home", "Work", "not_home") to a zone entity id."""
        if person_state == STATE_HOME:
            return ZONE_HOME
        for zone in self.hass.states.async_all("zone"):
            if zone.name == person_state:
                return zone.entity_id
        return None

    @callback
    def _process(self, state: State) -> None:
        if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return

        zone = self._resolve_zone(state.state)
        if zone == self.current_zone:
            return

        now = dt_util.utcnow()
        if self.current_zone is not None:
            self.last_left_zone = self.current_zone
            self.left_at = now

        self.current_zone = zone
        if zone is not None:
            origin = self.last_left_zone
            self.arrived_at = now
            if origin is not None and origin != zone:
                self.previous_zone = origin
                self._fire_transition(origin, zone)

        self._store.async_delay_save(self._data_to_save, 1)
        async_dispatcher_send(self.hass, signal_updated(self.entry_id))

    def _fire_transition(self, from_zone: str, to_zone: str) -> None:
        travel_seconds = (
            (self.arrived_at - self.left_at).total_seconds()
            if self.arrived_at and self.left_at
            else None
        )
        self.hass.bus.async_fire(
            EVENT_ZONE_TRANSITION,
            {
                "entity_id": self.person_id,
                "device_id": self.device_id,
                "from_zone": from_zone,
                "from_zone_name": self.zone_name(from_zone),
                "to_zone": to_zone,
                "to_zone_name": self.zone_name(to_zone),
                "left_at": _format_dt(self.left_at),
                "arrived_at": _format_dt(self.arrived_at),
                "travel_seconds": travel_seconds,
            },
        )

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "current_zone": self.current_zone,
            "arrived_at": _format_dt(self.arrived_at),
            "last_left_zone": self.last_left_zone,
            "left_at": _format_dt(self.left_at),
            "previous_zone": self.previous_zone,
        }
