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
        GrokVoicePersonalityVectorSensor(coordinator, entry),
        GrokVoicePersonalityAspectSensor(coordinator, entry, "warmth", "Warmth"),
        GrokVoicePersonalityAspectSensor(coordinator, entry, "verbosity", "Verbosity"),
        GrokVoicePersonalityAspectSensor(coordinator, entry, "humor", "Humor"),
        GrokVoicePersonalityAspectSensor(coordinator, entry, "energy", "Energy"),
        GrokVoicePersonalityAspectSensor(coordinator, entry, "caution", "Caution"),
        GrokVoicePersonalityAspectSensor(coordinator, entry, "creativity", "Creativity"),
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
        
class GrokVoicePersonalityVectorSensor(GrokVoiceBaseSensor):
    """Summary personality vector + fragment attributes."""

    def __init__(self, coordinator: GrokVoiceDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "personality_vector", "Personality Vector")
        self._attr_icon = "mdi:chart-radar"

    @property
    def native_value(self) -> str | None:
        vec = self.coordinator.data.get("personality_vector") or {}
        if not vec:
            return "unknown"
        # Compact fingerprint for history (e.g. w0.51/c0.25/cr0.00)
        parts = [f"{k[:2]}{float(v):.2f}" for k, v in sorted(vec.items())]
        return "/".join(parts)[:255]

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        attrs = dict(data.get("personality_vector") or {})
        attrs["fragment"] = data.get("personality_fragment") or ""
        attrs["fragment_updated_at"] = data.get("personality_fragment_updated_at")
        attrs["modulator_count"] = data.get("personality_modulator_count", 0)
        return attrs


class GrokVoicePersonalityAspectSensor(GrokVoiceBaseSensor):
    """Single aspect score 0.0–1.0 for history charts."""

    def __init__(
        self,
        coordinator: GrokVoiceDataUpdateCoordinator,
        entry: ConfigEntry,
        aspect: str,
        name: str,
    ) -> None:
        super().__init__(coordinator, entry, f"personality_{aspect}", f"Personality {name}")
        self._aspect = aspect
        self._attr_icon = "mdi:gauge"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = None
        self._attr_suggested_display_precision = 3

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get(f"personality_{self._aspect}")
        if val is None:
            return None
        try:
            return round(float(val), 4)
        except (TypeError, ValueError):
            return None
