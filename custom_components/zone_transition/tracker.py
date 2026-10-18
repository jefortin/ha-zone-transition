"""Zone history tracking for every person."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.const import (
    EVENT_STATE_CHANGED,
    STATE_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    EVENT_ZONE_TRANSITION,
    SIGNAL_PERSON_ADDED,
    STORAGE_KEY,
    STORAGE_VERSION,
    signal_updated,
)

PERSON_DOMAIN = "person"
ZONE_HOME = "zone.home"


def _parse_dt(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _format_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class PersonHistory:
    """The zones one person has been in."""

    def __init__(self, person_id: str, data: dict[str, Any] | None = None) -> None:
        data = data or {}
        self.person_id = person_id
        self.current_zone: str | None = data.get("current_zone")
        self.arrived_at = _parse_dt(data.get("arrived_at"))
        self.last_left_zone: str | None = data.get("last_left_zone")
        self.left_at = _parse_dt(data.get("left_at"))
        self.previous_zone: str | None = data.get("previous_zone")

    @property
    def last_known_zone(self) -> str | None:
        """The zone the person is in, or the last one they were in."""
        return self.current_zone or self.last_left_zone

    def as_dict(self) -> dict[str, Any]:
        return {
            "current_zone": self.current_zone,
            "arrived_at": _format_dt(self.arrived_at),
            "last_left_zone": self.last_left_zone,
            "left_at": _format_dt(self.left_at),
            "previous_zone": self.previous_zone,
        }


class ZoneTransitionManager:
    """Follows every person entity and fires an event on zone-to-zone moves.

    Passing through "not_home" is ignored, so home -> not_home -> work is
    reported as a single home -> work transition.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.people: dict[str, PersonHistory] = {}
        self._store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )

    def zone_name(self, zone_id: str | None) -> str | None:
        """Friendly name of a zone entity, falling back to its entity id."""
        if zone_id is None:
            return None
        state = self.hass.states.get(zone_id)
        return state.name if state else zone_id

    async def async_start(self) -> CALLBACK_TYPE:
        """Restore saved history, catch up with current states and start listening."""
        saved = await self._store.async_load() or {}
        for person_id, data in saved.items():
            self.people[person_id] = PersonHistory(person_id, data)

        # Catch up on anything that happened while we were not running.
        for state in self.hass.states.async_all(PERSON_DOMAIN):
            self._process(state)

        @callback
        def _state_changed(event: Event[EventStateChangedData]) -> None:
            if (new_state := event.data["new_state"]) is not None:
                self._process(new_state)

        @callback
        def _is_person(event_data: EventStateChangedData) -> bool:
            return event_data["entity_id"].startswith(f"{PERSON_DOMAIN}.")

        return self.hass.bus.async_listen(
            EVENT_STATE_CHANGED, _state_changed, event_filter=_is_person
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

        if (person := self.people.get(state.entity_id)) is None:
            person = self.people[state.entity_id] = PersonHistory(state.entity_id)
            async_dispatcher_send(self.hass, SIGNAL_PERSON_ADDED, state.entity_id)

        zone = self._resolve_zone(state.state)
        if zone == person.current_zone:
            return

        now = dt_util.utcnow()
        if person.current_zone is not None:
            person.last_left_zone = person.current_zone
            person.left_at = now

        person.current_zone = zone
        if zone is not None:
            origin = person.last_left_zone
            person.arrived_at = now
            if origin is not None and origin != zone:
                person.previous_zone = origin
                self._fire_transition(person, state)

        self._store.async_delay_save(self._data_to_save, 1)
        async_dispatcher_send(self.hass, signal_updated(person.person_id))

    def _fire_transition(self, person: PersonHistory, state: State) -> None:
        travel_seconds = (
            (person.arrived_at - person.left_at).total_seconds()
            if person.arrived_at and person.left_at
            else None
        )
        self.hass.bus.async_fire(
            EVENT_ZONE_TRANSITION,
            {
                "entity_id": person.person_id,
                "from_zone": person.previous_zone,
                "from_zone_name": self.zone_name(person.previous_zone),
                "to_zone": person.current_zone,
                "to_zone_name": self.zone_name(person.current_zone),
                "left_at": _format_dt(person.left_at),
                "arrived_at": _format_dt(person.arrived_at),
                "travel_seconds": travel_seconds,
            },
            context=state.context,
        )

    @callback
    def _data_to_save(self) -> dict[str, dict[str, Any]]:
        return {person_id: p.as_dict() for person_id, p in self.people.items()}
