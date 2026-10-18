"""Sensors exposing each person's zone history."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZoneTransitionConfigEntry
from .const import SIGNAL_PERSON_ADDED, signal_updated
from .tracker import PersonHistory, ZoneTransitionManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneTransitionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager = entry.runtime_data

    # The "previous zone" sensor was removed in 0.3.0.
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id.endswith("_previous_zone"):
            registry.async_remove(entity.entity_id)

    @callback
    def _add_person(person_id: str) -> None:
        person = manager.people[person_id]
        async_add_entities([LastKnownZoneSensor(manager, person)])

    for person_id in manager.people:
        _add_person(person_id)
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_PERSON_ADDED, _add_person)
    )


class _ZoneSensorBase(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:map-marker-path"

    def __init__(self, manager: ZoneTransitionManager, person: PersonHistory) -> None:
        self.manager = manager
        self.person = person
        self._attr_unique_id = f"{person.person_id}_{self.translation_key}"
        person_state = manager.hass.states.get(person.person_id)
        self._attr_translation_placeholders = {
            "person": person_state.name if person_state else person.person_id
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_updated(self.person.person_id), self.async_write_ha_state
            )
        )


class LastKnownZoneSensor(_ZoneSensorBase):
    """The zone the person is in, or the last zone they were in while away."""

    _attr_translation_key = "last_known_zone"

    @property
    def native_value(self) -> str | None:
        return self.manager.zone_name(self.person.last_known_zone)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        p = self.person
        return {
            "person": p.person_id,
            "zone": p.last_known_zone,
            "in_zone": p.current_zone is not None,
            "arrived_at": p.arrived_at,
            "left_at": None if p.current_zone else p.left_at,
        }

