"""The Grok Voice Home Assistant custom component."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_STATE_PUSH_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import GrokVoiceDataUpdateCoordinator
from .personality import PersonalityTracker

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grok Voice from a config entry."""
    session = async_get_clientsession(hass)

    coordinator = GrokVoiceDataUpdateCoordinator(
        hass=hass,
        entry=entry,
        session=session,
    )

    tracker = PersonalityTracker(
        hass=hass,
        entry_id=entry.entry_id,
        get_modulators=coordinator.get_modulators,
        post_states=coordinator.async_post_personality_states,
        interval_seconds=DEFAULT_STATE_PUSH_INTERVAL,
    )
    coordinator.personality_tracker = tracker

    await coordinator.async_config_entry_first_refresh()
    await tracker.async_start()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: GrokVoiceDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator and coordinator.personality_tracker:
        await coordinator.personality_tracker.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)