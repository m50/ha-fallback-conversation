import asyncio

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.components.sensor import ENTITY_ID_FORMAT

class FallbackResultEntity():
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
    
    @callback
    def add_to_platform_start(
        self,
        hass: HomeAssistant,
        platform: EntityPlatform,
        parallel_updates: asyncio.Semaphore | None,
    ) -> None:
        """Start adding an entity to a platform."""
        super().add_to_platform_start(hass, platform, parallel_updates)

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._state = state.state
            self._attributes = dict(state.attributes)

    def update_result(self, agent_name, response):
        """Update the entity with the latest fallback result."""
        self._state = agent_name
        self._attributes = {
            "response": response,
            "timestamp": self.hass.states.get(self.entity_id).last_updated.isoformat()
        }
        self.async_write_ha_state()