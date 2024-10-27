import asyncio

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.components.conversation.models import ConversationResult

class FallbackResultEntity(SensorEntity):
    """Entity to store the latest fallback result."""

    def __init__(self, hass: HomeAssistant, unique_id):
        """Initialize the entity."""
        self.hass = hass
        self._unique_id = unique_id
        self._state = None
        self._attributes = {}
        self.entity_id = ENTITY_ID_FORMAT.format(unique_id)

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the entity."""
        return "Fallback Conversation Result"

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._state = state.state
            self._attributes = dict(state.attributes)

    def update_result(self, agent_name, prompt: str, result: ConversationResult):
        """Update the entity with the latest fallback result."""

        plain_text_response = ""
        if result.response.speech['plain']['original_speech']:
            plain_text_response = result.response.speech['plain']['original_speech']

        formatted_state: str = f"""
        [Agent]:{agent_name},
        [Prompt]:{prompt},
        [Response]:{plain_text_response}
        """

        #truncate to 255 characters
        if len(formatted_state) > 255:
            formatted_state = formatted_state[:255]

        self._state = formatted_state
        self._attributes = result.response.as_dict()
        self._attributes["Full State"] = formatted_state
        self.async_write_ha_state()