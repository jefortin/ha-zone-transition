"""Sensors exposing a person's zone history."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ZoneTransitionConfigEntry
from .const import DOMAIN, signal_updated
from .tracker import ZoneTracker


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ZoneTransitionConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    tracker = entry.runtime_data
    async_add_entities(
        [LastKnownZoneSensor(tracker, entry), PreviousZoneSensor(tracker, entry)]
    )


class _ZoneSensorBase(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:map-marker-path"

    def __init__(self, tracker: ZoneTracker, entry: ZoneTransitionConfigEntry) -> None:
        self.tracker = tracker
        self._attr_unique_id = f"{entry.entry_id}_{self.translation_key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_updated(self.tracker.entry_id), self.async_write_ha_state
            )
        )


class LastKnownZoneSensor(_ZoneSensorBase):
    """The zone the person is in, or the last zone they were in while away."""

    _attr_translation_key = "last_known_zone"

    @property
    def native_value(self) -> str | None:
        return self.tracker.zone_name(self.tracker.last_known_zone)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        t = self.tracker
        return {
            "zone": t.last_known_zone,
            "in_zone": t.current_zone is not None,
            "arrived_at": t.arrived_at,
            "left_at": None if t.current_zone else t.left_at,
        }


class PreviousZoneSensor(_ZoneSensorBase):
    """The zone the person was in before their last known zone."""

    _attr_translation_key = "previous_zone"

    @property
    def native_value(self) -> str | None:
        return self.tracker.zone_name(self.tracker.previous_zone)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"zone": self.tracker.previous_zone}
