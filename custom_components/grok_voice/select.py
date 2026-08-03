"""Select platform for Grok Voice."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODEL_OPTIONS, UNIQUE_ID_PREFIX, VOICE_OPTIONS
from .coordinator import GrokVoiceDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grok Voice select entities."""
    coordinator: GrokVoiceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GrokVoiceVoiceSelect(coordinator, entry),
        GrokVoiceModelSelect(coordinator, entry),
    ]
    async_add_entities(entities)


class GrokVoiceBaseSelect(CoordinatorEntity[GrokVoiceDataUpdateCoordinator], SelectEntity):
    """Base class for Grok Voice selects."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GrokVoiceDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        options: list[str],
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{UNIQUE_ID_PREFIX}_{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_options = options
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grok Voice Microservice",
            "manufacturer": "xAI / KeithSBB",
            "model": "Grok Voice",
        }

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.get(self._key)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_set_config(self._key, option)


class GrokVoiceVoiceSelect(GrokVoiceBaseSelect):
    """Voice select."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            key="voice",
            name="Voice",
            options=VOICE_OPTIONS,
        )
        self._attr_icon = "mdi:account-voice"


class GrokVoiceModelSelect(GrokVoiceBaseSelect):
    """Model select."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator,
            entry,
            key="model",
            name="Model",
            options=MODEL_OPTIONS,
        )
        self._attr_icon = "mdi:brain"
