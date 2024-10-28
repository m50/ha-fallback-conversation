import asyncio

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.conversation.models import ConversationResult

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Set up Fallback Conversation from a config entry."""
    result_entity = FallbackResultEntity(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["result_entity"] = result_entity
    async_add_entities([result_entity])
    return True

class FallbackResultEntity(SensorEntity, RestoreEntity):
    """Entity to store the latest fallback result."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize the entity."""
        self
        self.hass = hass
        self.entry = entry
        self._attr_name = f"{entry.title} Result"
        self._attr_unique_id = f"{entry.entry_id}_result"
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Return the name of the entity."""
        return self._attr_name

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
