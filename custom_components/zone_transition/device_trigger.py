"""Device trigger: person moved from one zone to another."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_FROM_ZONE,
    CONF_TO_ZONE,
    DOMAIN,
    EVENT_ZONE_TRANSITION,
    TRIGGER_TYPE_TRANSITION,
)

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In({TRIGGER_TYPE_TRANSITION}),
        vol.Optional(CONF_FROM_ZONE): cv.entity_domain("zone"),
        vol.Optional(CONF_TO_ZONE): cv.entity_domain("zone"),
    }
)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: TRIGGER_TYPE_TRANSITION,
        }
    ]


async def async_get_trigger_capabilities(
    hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    zone_selector = selector.EntitySelector(selector.EntitySelectorConfig(domain="zone"))
    return {
        "extra_fields": vol.Schema(
            {
                vol.Optional(CONF_FROM_ZONE): zone_selector,
                vol.Optional(CONF_TO_ZONE): zone_selector,
            }
        )
    }


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    event_data = {"device_id": config[CONF_DEVICE_ID]}
    for key in (CONF_FROM_ZONE, CONF_TO_ZONE):
        if key in config:
            event_data[key] = config[key]

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: EVENT_ZONE_TRANSITION,
            event_trigger.CONF_EVENT_DATA: event_data,
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
