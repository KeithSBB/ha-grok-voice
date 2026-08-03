"""Text platform for Grok Voice (system prompt)."""
from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SYSTEM_PROMPT_MAX_LENGTH, UNIQUE_ID_PREFIX
from .coordinator import GrokVoiceDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grok Voice text entities."""
    coordinator: GrokVoiceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([GrokVoiceSystemPromptText(coordinator, entry)])


class GrokVoiceSystemPromptText(
    CoordinatorEntity[GrokVoiceDataUpdateCoordinator], TextEntity
):
    """System prompt text entity (supports long prompts)."""

    _attr_has_entity_name = True
    _attr_mode = TextMode.TEXT
    _attr_native_max = SYSTEM_PROMPT_MAX_LENGTH
    _attr_icon = "mdi:text-box-outline"

    def __init__(
        self,
        coordinator: GrokVoiceDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{UNIQUE_ID_PREFIX}_{entry.entry_id}_system_prompt"
        self._attr_name = "System Prompt"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grok Voice Microservice",
            "manufacturer": "xAI / KeithSBB",
            "model": "Grok Voice",
        }

    @property
    def native_value(self) -> str | None:
        """Return the full system prompt (used by the text UI)."""
        return self.coordinator.data.get("system_prompt")

    @property
    def state(self) -> str | None:
        """
        Core state machine still enforces a 255-char limit.
        Return a truncated version so the entity stays available.
        The full value remains available via native_value for editing.
        """
        value = self.native_value or ""
        if len(value) > 255:
            return value[:252] + "..."
        return value

    async def async_set_value(self, value: str) -> None:
        """Set the system prompt."""
        await self.coordinator.async_set_config("system_prompt", value)