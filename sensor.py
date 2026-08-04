"""Sensor platform for Grok Voice."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
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
    """Set up Grok Voice sensors."""
    coordinator: GrokVoiceDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        GrokVoiceStatusSensor(coordinator, entry),
        GrokVoiceInputTokensSensor(coordinator, entry),
        GrokVoiceOutputTokensSensor(coordinator, entry),
        GrokVoiceEstimatedCostSensor(coordinator, entry),
        GrokVoiceActiveSatellitesSensor(coordinator, entry),
        GrokVoicePersonalitySyncSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class GrokVoiceBaseSensor(CoordinatorEntity[GrokVoiceDataUpdateCoordinator], SensorEntity):
    """Base class for Grok Voice sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GrokVoiceDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{UNIQUE_ID_PREFIX}_{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grok Voice Microservice",
            "manufacturer": "xAI / KeithSBB",
            "model": "Grok Voice",
        }


class GrokVoiceStatusSensor(GrokVoiceBaseSensor):
    """Service status sensor."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "status", "Service Status")
        self._attr_icon = "mdi:robot"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("status")


class GrokVoiceInputTokensSensor(GrokVoiceBaseSensor):
    """Input token count."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "input_tokens", "Input Tokens")
        self._attr_icon = "mdi:arrow-up-bold"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("input_tokens")


class GrokVoiceOutputTokensSensor(GrokVoiceBaseSensor):
    """Output token count."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "output_tokens", "Output Tokens")
        self._attr_icon = "mdi:arrow-down-bold"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("output_tokens")


class GrokVoiceEstimatedCostSensor(GrokVoiceBaseSensor):
    """Estimated cost sensor."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "estimated_cost", "Estimated Cost")
        self._attr_icon = "mdi:currency-usd"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_native_unit_of_measurement = "USD"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("estimated_cost")


class GrokVoiceActiveSatellitesSensor(GrokVoiceBaseSensor):
    """Active satellite count."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "active_satellites", "Active Satellites")
        self._attr_icon = "mdi:speaker-multiple"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get("active_satellites")
        
class GrokVoicePersonalitySyncSensor(GrokVoiceBaseSensor):
    """Personality sync status."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "personality_sync", "Personality Sync")
        self._attr_icon = "mdi:brain"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.get("personality_sync")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "last_sync_at": self.coordinator.data.get("personality_last_sync_at"),
            "last_error": self.coordinator.data.get("personality_last_error"),
            "modulator_count": self.coordinator.data.get("personality_modulator_count", 0),
        }
