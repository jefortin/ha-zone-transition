"""Automation trigger: a person moved from one zone to another."""

from __future__ import annotations

from typing import Any, override

import probatio

from homeassistant.const import CONF_OPTIONS, CONF_TARGET
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.helpers.trigger import (
    Trigger,
    TriggerActionRunner,
    TriggerConfig,
    TriggerNotTriggeredReporter,
)
from homeassistant.helpers.typing import ConfigType

from .const import CONF_FROM_ZONE, CONF_TO_ZONE, EVENT_ZONE_TRANSITION

_CONFIG_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_TARGET): cv.TARGET_FIELDS,
        probatio.Required(CONF_OPTIONS, default={}): {
            probatio.Optional(CONF_FROM_ZONE): cv.entity_domain("zone"),
            probatio.Optional(CONF_TO_ZONE): cv.entity_domain("zone"),
        },
    }
)


class MovedTrigger(Trigger):
    """Fires when a targeted person arrives in a zone coming from another zone."""

    @classmethod
    @override
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        return _CONFIG_SCHEMA(config)

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        super().__init__(hass, config)
        assert config.target is not None
        self._target = TargetSelection(config.target)
        options = config.options or {}
        self._from_zone: str | None = options.get(CONF_FROM_ZONE)
        self._to_zone: str | None = options.get(CONF_TO_ZONE)

    def _targets(self, entity_id: str) -> bool:
        # Resolved on every event so targets picked by area or label stay current.
        selected = async_extract_referenced_entity_ids(self._hass, self._target)
        return entity_id in selected.referenced | selected.indirectly_referenced

    @override
    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None = None,
    ) -> CALLBACK_TYPE:
        @callback
        def _transition(event: Event[dict[str, Any]]) -> None:
            data = event.data
            if self._from_zone and data["from_zone"] != self._from_zone:
                return
            if self._to_zone and data["to_zone"] != self._to_zone:
                return
            if not self._targets(data["entity_id"]):
                return

            person = self._hass.states.get(data["entity_id"])
            name = person.name if person else data["entity_id"]
            run_action(
                dict(data),
                f"{name} moved from {data['from_zone_name']} to {data['to_zone_name']}",
                event.context,
            )

        return self._hass.bus.async_listen(EVENT_ZONE_TRANSITION, _transition)


TRIGGERS: dict[str, type[Trigger]] = {
    "moved": MovedTrigger,
}


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Return the triggers for Zone Transition."""
    return TRIGGERS
