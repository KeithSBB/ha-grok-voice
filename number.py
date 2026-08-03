"""Number platform for Grok Voice."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, UNIQUE_ID_PREFIX
from .coordinator import GrokVoiceDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grok Voice number entities."""
    coordinator: GrokVoiceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GrokVoiceConversationTimeoutNumber(coordinator, entry),
        GrokVoiceConversationPersistenceNumber(coordinator, entry),
    ]
    async_add_entities(entities)


class GrokVoiceBaseNumber(CoordinatorEntity[GrokVoiceDataUpdateCoordinator], NumberEntity):
    """Base class for Grok Voice numbers."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: GrokVoiceDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        min_value: float,
        max_value: float,
        step: float,
        unit: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{UNIQUE_ID_PREFIX}_{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grok Voice Microservice",
            "manufacturer": "xAI / KeithSBB",
            "model": "Grok Voice",
        }

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get(self._key)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.coordinator.async_set_config(self._key, int(value))


class GrokVoiceConversationTimeoutNumber(GrokVoiceBaseNumber):
    """Conversation timeout (seconds)."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            key="conversation_timeout_seconds",
            name="Conversation Timeout",
            min_value=1,
            max_value=120,
            step=1,
            unit="s",
        )
        self._attr_icon = "mdi:timer-outline"


class GrokVoiceConversationPersistenceNumber(GrokVoiceBaseNumber):
    """Conversation persistence (seconds)."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            key="conversation_persistence_seconds",
            name="Conversation Persistence",
            min_value=0,
            max_value=3600,
            step=10,
            unit="s",
        )
        self._attr_icon = "mdi:timer-sand"
