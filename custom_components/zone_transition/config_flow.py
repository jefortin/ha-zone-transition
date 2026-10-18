"""Config flow for Zone Transition."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import CONF_PERSON, DOMAIN


class ZoneTransitionConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add one entry per tracked person."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            person_id = user_input[CONF_PERSON]
            await self.async_set_unique_id(person_id)
            self._abort_if_unique_id_configured()

            state = self.hass.states.get(person_id)
            title = state.name if state else person_id
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PERSON): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="person")
                    )
                }
            ),
        )
