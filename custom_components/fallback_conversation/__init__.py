"""Fallback Conversation Agent"""
from __future__ import annotations

import logging

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import ulid
from home_assistant_intents import get_languages


from homeassistant.helpers import (
    config_validation as cv,
    intent,
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

    last_used_agent: str | None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.last_used_agent = None

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return get_languages()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        agent_manager = conversation._get_agent_manager(self.hass)
        agent_names = self._convert_agent_info_to_dict(agent_manager.async_get_agent_info())
        agents = [
            self.entry.options.get(CONF_PRIMARY_AGENT, agent_manager.default_agent), 
            self.entry.options.get(CONF_FALLBACK_AGENT, agent_manager.default_agent),
        ]

        debug_level = self.entry.options.get(CONF_DEBUG_LEVEL, DEBUG_LEVEL_NO_DEBUG)

        if user_input.conversation_id is None:
            user_input.conversation_id = ulid.ulid()

        all_results = []
        result = None
        for agent_id in agents:
            result = await self._async_process_agent(
                agent_manager, 
                agent_id, 
                agent_names[agent_id], 
                user_input, 
                debug_level,
                result,
            )
            if result.response.response_type != intent.IntentResponseType.ERROR:
                return result
            all_results.append(result)

        intent_response = intent.IntentResponse(language=user_input.language)
        err = "Complete fallback failure. No Conversation Agent was able to respond."
        if debug_level == DEBUG_LEVEL_LOW_DEBUG:
            r = all_results[-1].response.speech['plain']
            err += f"\n{r.get('agent_name', 'UNKNOWN')} responded with: {r.get('original_speech', r['speech'])}"
        elif debug_level == DEBUG_LEVEL_VERBOSE_DEBUG:
            for res in all_results:
                r = res.response.speech['plain']
                err += f"\n{r.get('agent_name', 'UNKNOWN')} responded with: {r.get('original_speech', r['speech'])}"
        intent_response.async_set_error(
            intent.IntentResponseErrorCode.NO_INTENT_MATCH,
            err,
        )
        result = conversation.ConversationResult(
            conversation_id=result.conversation_id,
            response=intent_response
        )
    
        return result

    async def _async_process_agent(
        self, 
        agent_manager: conversation.AgentManager, 
        agent_id: str,
        agent_name: str,
        user_input: conversation.ConversationInput, 
        debug_level: int,
        previous_result,
    ) -> conversation.ConversationResult:
        """Process a specified agent."""
        agent = await agent_manager.async_get_agent(agent_id)

        _LOGGER.debug("Processing in %s using %s with debug level %s: %s", user_input.language, agent_id, debug_level, user_input.text)

        result = await agent.async_process(user_input)
        r = result.response.speech['plain']['speech']
        result.response.speech['plain']['original_speech'] = r
        result.response.speech['plain']['agent_name'] = agent_name
        result.response.speech['plain']['agent_id'] = agent_id
        if debug_level == DEBUG_LEVEL_LOW_DEBUG:
            result.response.speech['plain']['speech'] = f"{agent_name} responded with: {r}"
        elif debug_level == DEBUG_LEVEL_VERBOSE_DEBUG:
            if previous_result is not None:
                pr = previous_result.response.speech['plain'].get('original_speech', previous_result.response.speech['plain']['speech'])
                result.response.speech['plain']['speech'] = f"{previous_result.response.speech['plain'].get('agent_name', 'UNKNOWN')} failed with response: {pr} Then {agent_name} responded with {r}"
            else:
                result.response.speech['plain']['speech'] = f"{agent_name} responded with: {r}"

        return result

    def _convert_agent_info_to_dict(self, agents: list[conversation.AgentInfo]) -> dict[str, str]:
        """Takes a list of AgentInfo and makes it a dict of ID -> Name."""
        r = {}
        for agent in agents:
            r[agent.id] = agent.name

        return r


