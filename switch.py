"""Switch platform for Grok Voice."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    coordinator: GrokVoiceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([GrokVoiceWebSearchSwitch(coordinator, entry)])


class GrokVoiceWebSearchSwitch(
    CoordinatorEntity[GrokVoiceDataUpdateCoordinator], SwitchEntity
):
    """Enable/disable xAI web_search for voice sessions (next session start)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:web"
    _attr_name = "Web Search"

    def __init__(
        self,
        coordinator: GrokVoiceDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{UNIQUE_ID_PREFIX}_{entry.entry_id}_web_search"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grok Voice Microservice",
            "manufacturer": "xAI / KeithSBB",
            "model": "Grok Voice",
        }

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("web_search", False))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_config("web_search", True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_config("web_search", False)