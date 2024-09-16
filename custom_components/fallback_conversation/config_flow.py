"""Config flow for Fallback Conversation integration."""
from __future__ import annotations

import logging
# from types import MappingProxyType
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    ConversationAgentSelector,
    ConversationAgentSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
    SelectSelectorMode,
)

from .const import (
    CONF_DEBUG_LEVEL,
    CONF_PRIMARY_AGENT,
    CONF_FALLBACK_AGENT,
    DEBUG_LEVEL_NO_DEBUG,
    DEBUG_LEVEL_LOW_DEBUG,
    DEBUG_LEVEL_VERBOSE_DEBUG,
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_DEBUG_LEVEL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_DEBUG_LEVEL, default=DEFAULT_DEBUG_LEVEL): SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=DEBUG_LEVEL_NO_DEBUG, label="No Debug"),
                    SelectOptionDict(value=DEBUG_LEVEL_LOW_DEBUG, label="Some Debug"),
                    SelectOptionDict(value=DEBUG_LEVEL_VERBOSE_DEBUG, label="Verbose Debug"),
                ],
                mode=SelectSelectorMode.DROPDOWN
            ),
        ),
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Fallback Agent config flow."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.debug("ConfigFlow::user_input %s", user_input)
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        return self.async_create_entry(
            title=user_input.get(CONF_NAME, DEFAULT_NAME),
            data=user_input,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlow(config_entry)

class OptionsFlow(config_entries.OptionsFlow):
    """Fallback config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._options = dict(config_entry.data)
        self._options.update(dict(config_entry.options))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data=self._options,
            )

        schema = await self.fallback_config_option_schema(self._options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )

    async def fallback_config_option_schema(self, options: dict) -> dict:
        """Return a schema for Fallback options."""
        return {
            vol.Required(
                CONF_DEBUG_LEVEL,
                description={"suggested_value": options.get(CONF_DEBUG_LEVEL, DEFAULT_DEBUG_LEVEL)},
                default=DEFAULT_DEBUG_LEVEL,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=DEBUG_LEVEL_NO_DEBUG, label="No Debug"),
                        SelectOptionDict(value=DEBUG_LEVEL_LOW_DEBUG, label="Some Debug"),
                        SelectOptionDict(value=DEBUG_LEVEL_VERBOSE_DEBUG, label="Verbose Debug"),
                    ],
                    mode=SelectSelectorMode.DROPDOWN
                ),
            ),
            vol.Required(
                CONF_PRIMARY_AGENT,
                description={"suggested_value": options.get(CONF_PRIMARY_AGENT, "homeassistant")},
                default="homeassistant",
            ): ConversationAgentSelector(ConversationAgentSelectorConfig()),
            vol.Required(
                CONF_FALLBACK_AGENT,
                description={"suggested_value": options.get(CONF_FALLBACK_AGENT, "")},
            ): ConversationAgentSelector(ConversationAgentSelectorConfig()),
        };