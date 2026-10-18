"""Zone Transition: remember where a person was and trigger on zone-to-zone moves."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_PERSON, DOMAIN
from .tracker import ZoneTracker

PLATFORMS = [Platform.SENSOR]

type ZoneTransitionConfigEntry = ConfigEntry[ZoneTracker]


async def async_setup_entry(hass: HomeAssistant, entry: ZoneTransitionConfigEntry) -> bool:
    """Set up a tracker for one person."""
    tracker = ZoneTracker(hass, entry.entry_id, entry.data[CONF_PERSON])

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        entry_type=dr.DeviceEntryType.SERVICE,
    )
    tracker.device_id = device.id

    await tracker.async_start()
    entry.runtime_data = tracker
    entry.async_on_unload(tracker.async_listen())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZoneTransitionConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
