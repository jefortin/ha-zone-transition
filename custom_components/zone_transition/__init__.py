"""Zone Transition: remember where people were and trigger on zone-to-zone moves."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .tracker import ZoneTransitionManager

PLATFORMS = [Platform.SENSOR]

type ZoneTransitionConfigEntry = ConfigEntry[ZoneTransitionManager]


async def async_setup_entry(hass: HomeAssistant, entry: ZoneTransitionConfigEntry) -> bool:
    """Start tracking every person."""
    manager = ZoneTransitionManager(hass)
    entry.async_on_unload(await manager.async_start())
    entry.runtime_data = manager

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZoneTransitionConfigEntry) -> bool:
    """Unload the config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
