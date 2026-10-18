"""Constants for the Zone Transition integration."""

DOMAIN = "zone_transition"

CONF_PERSON = "person"
CONF_FROM_ZONE = "from_zone"
CONF_TO_ZONE = "to_zone"

EVENT_ZONE_TRANSITION = f"{DOMAIN}_transition"
TRIGGER_TYPE_TRANSITION = "zone_transition"

STORAGE_VERSION = 1


def signal_updated(entry_id: str) -> str:
    """Dispatcher signal sent when a tracker's state changes."""
    return f"{DOMAIN}_{entry_id}_updated"
