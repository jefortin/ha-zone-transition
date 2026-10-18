"""Constants for the Zone Transition integration."""

DOMAIN = "zone_transition"

CONF_FROM_ZONE = "from_zone"
CONF_TO_ZONE = "to_zone"

EVENT_ZONE_TRANSITION = f"{DOMAIN}_transition"

SIGNAL_PERSON_ADDED = f"{DOMAIN}_person_added"

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1


def signal_updated(person_id: str) -> str:
    """Dispatcher signal sent when a person's zone history changes."""
    return f"{DOMAIN}_{person_id}_updated"
