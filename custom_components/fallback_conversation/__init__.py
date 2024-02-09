"""Fallback Conversation Agent"""
from __future__ import annotations

import logging
from typing import Literal
import json
import yaml

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid
from home_assistant_intents import get_languages
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.exceptions import (
    HomeAssistantError,
)

from homeassistant.helpers import (
    config_validation as cv,
    intent,
    template,
    entity_registry as er,
)

from .const import (
    CONF_DEBUG_LEVEL,
    CONF_PRIMARY_AGENT,
    CONF_FALLBACK_AGENT,
    DEBUG_LEVEL_NO_DEBUG,
    DEBUG_LEVEL_LOW_DEBUG,
    DEBUG_LEVEL_VERBOSE_DEBUG,
    DOMAIN,
)


_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


# hass.data key for agent.
DATA_AGENT = "agent"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fallback Conversation Agent from a config entry."""
    agent = FallbackConversationAgent(hass, entry)

    conversation.async_set_agent(hass, entry, agent)

    return True


class FallbackConversationAgent(conversation.AbstractConversationAgent):
    """Fallback Conversation Agent."""

    agent_manager: conversation.AgentManager

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return get_languages()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        agent_manager = conversation._get_agent_manager(self.hass)
        agents = [
            self.entry.options.get(CONF_PRIMARY_AGENT, agent_manager.default_agent), 
            self.entry.options.get(CONF_FALLBACK_AGENT, agent_manager.default_agent),
        ]

        debug_level = self.entry.options.get(CONF_DEBUG_LEVEL, DEBUG_LEVEL_NO_DEBUG)

        if user_input.conversation_id is None:
            user_input.conversation_id = ulid.ulid()

        for agent_id in agents:
            result = await self._async_process_agent(agent_manager, agent_id, user_input, debug_level);
            if result.response.response_type != intent.IntentResponseType.ERROR:
                return result

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech("Complete fallback failure")
        result = conversation.ConversationResult(
            conversation_id=result.conversation_id,
            response=intent_response
        )
    
        return result

    async def _async_process_agent(
        self, 
        agent_manager: conversation.AgentManager, 
        agent_id: str, 
        user_input: conversation.ConversationInput, 
        debug_level: int
    ) -> conversation.ConversationResult:
        """Process a specified agent."""
        agent = await agent_manager.async_get_agent(agent_id)

        _LOGGER.debug("Processing in %s using %s with debug level %s: %s", user_input.language, agent_id, debug_level, user_input.text)

        result = await agent.async_process(user_input)
        if debug_level == DEBUG_LEVEL_VERBOSE_DEBUG:
            _LOGGER.debug("result %s", result.response.as_dict())

        return result


