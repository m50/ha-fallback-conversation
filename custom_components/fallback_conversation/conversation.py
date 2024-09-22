"""Fallback Conversation Agent"""
from __future__ import annotations

import logging

from homeassistant.components import assist_pipeline, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import ulid
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    STRANGE_ERROR_RESPONSES,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Set up Fallback Conversation from a config entry."""
    agent = FallbackConversationAgent(hass, entry)
    async_add_entities([agent])
    return True

class FallbackConversationAgent(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    """Fallback Conversation Agent."""

    last_used_agent: str | None

    entry: ConfigEntry
    hass: HomeAssistant

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.last_used_agent = None
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id
        self._attr_supported_features = (
            conversation.ConversationEntityFeature.CONTROL
        )
        self.in_context_examples = None

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return get_languages()

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        assist_pipeline.async_migrate_engine(
            self.hass, "conversation", self.entry.entry_id, self.entity_id
        )
        conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        self._attr_supported_features = (
            conversation.ConversationEntityFeature.CONTROL
        )

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        agent_manager = conversation.get_agent_manager(self.hass)
        default_agent = conversation.default_agent.async_get_default_agent(self.hass)
        agent_names = self._convert_agent_info_to_dict(
            agent_manager.async_get_agent_info()
        )
        agent_names[conversation.const.HOME_ASSISTANT_AGENT] = default_agent.name
        agent_names[conversation.const.OLD_HOME_ASSISTANT_AGENT] = default_agent.name
        agents = [
            self.entry.options.get(CONF_PRIMARY_AGENT, default_agent),
            self.entry.options.get(CONF_FALLBACK_AGENT, default_agent),
        ]

        debug_level = self.entry.options.get(CONF_DEBUG_LEVEL, DEBUG_LEVEL_NO_DEBUG)

        if user_input.conversation_id is None:
            user_input.conversation_id = ulid.ulid()

        all_results = []
        result = None
        for agent_id in agents:
            agent_name = "[unknown]"
            if agent_id in agent_names:
                agent_name = agent_names[agent_id]
            else:
                _LOGGER.warning("agent_name not found for agent_id %s", agent_id)

            result = await self._async_process_agent(
                agent_manager,
                agent_id,
                agent_name,
                user_input,
                debug_level,
                result,
            )
            if result.response.response_type != intent.IntentResponseType.ERROR and result.response.speech['plain']['original_speech'].lower() not in STRANGE_ERROR_RESPONSES:
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
        agent = conversation.agent_manager.async_get_agent(self.hass, agent_id)

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

    def _convert_agent_info_to_dict(self, agents_info: list[conversation.AgentInfo]) -> dict[str, str]:
        """Takes a list of AgentInfo and makes it a dict of ID -> Name."""

        agent_manager = conversation.get_agent_manager(self.hass)

        r = {}
        for agent_info in agents_info:
            agent = agent_manager.async_get_agent(agent_info.id)
            agent_id = agent_info.id
            if hasattr(agent, "registry_entry"):
                agent_id = agent.registry_entry.entity_id
            r[agent_id] = agent_info.name
            _LOGGER.debug("agent_id %s has name %s", agent_id, agent_info.name)
        return r