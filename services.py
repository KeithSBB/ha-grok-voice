"""Service handlers for Grok Voice personality modulators."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import ASPECT_OPTIONS, CURVE_OPTIONS, DOMAIN
from .coordinator import GrokVoiceDataUpdateCoordinator
from .personality import modulators_from_options

_LOGGER = logging.getLogger(__name__)

SERVICE_ADD = "add_modulator"
SERVICE_UPDATE = "update_modulator"
SERVICE_REMOVE = "remove_modulator"
SERVICE_SET_ENABLED = "set_modulator_enabled"


def _coordinator(hass: HomeAssistant) -> GrokVoiceDataUpdateCoordinator:
    data = hass.data.get(DOMAIN) or {}
    if not data:
        raise HomeAssistantError("Grok Voice is not set up")
    # Single instance expected
    return next(iter(data.values()))


def _normalize_entity(value: Any) -> str:
    if hasattr(value, "entity_id"):
        return str(value.entity_id)
    return str(value or "").strip()


async def _async_add(call: ServiceCall) -> None:
    coord = _coordinator(call.hass)
    mods = modulators_from_options(dict(coord.entry.options))

    eid = _normalize_entity(call.data["entity_id"])
    aspect = call.data["aspect"]
    mn = float(call.data["min"])
    mx = float(call.data["max"])
    if not eid:
        raise HomeAssistantError("entity_id is required")
    if aspect not in ASPECT_OPTIONS:
        raise HomeAssistantError(f"Invalid aspect: {aspect}")
    if mn >= mx:
        raise HomeAssistantError("min must be less than max")

    new_mod = {
        "id": str(uuid.uuid4()),
        "entity_id": eid,
        "aspect": aspect,
        "min": mn,
        "max": mx,
        "curve": call.data.get("curve") or "linear",
        "weight": float(call.data.get("weight", 1.0)),
        "invert": bool(call.data.get("invert", False)),
        "enabled": bool(call.data.get("enabled", True)),
    }
    if new_mod["curve"] not in CURVE_OPTIONS:
        raise HomeAssistantError(f"Invalid curve: {new_mod['curve']}")

    await coord.async_save_modulators(mods + [new_mod])
    _LOGGER.info("Added modulator %s → %s", new_mod["id"], eid)


async def _async_update(call: ServiceCall) -> None:
    coord = _coordinator(call.hass)
    mods = modulators_from_options(dict(coord.entry.options))
    mid = str(call.data["id"]).strip()
    found = False
    new_list: list[dict[str, Any]] = []
    for m in mods:
        if m["id"] != mid:
            new_list.append(m)
            continue
        found = True
        updated = dict(m)
        if "entity_id" in call.data:
            updated["entity_id"] = _normalize_entity(call.data["entity_id"])
        if "aspect" in call.data:
            if call.data["aspect"] not in ASPECT_OPTIONS:
                raise HomeAssistantError(f"Invalid aspect: {call.data['aspect']}")
            updated["aspect"] = call.data["aspect"]
        if "min" in call.data:
            updated["min"] = float(call.data["min"])
        if "max" in call.data:
            updated["max"] = float(call.data["max"])
        if "curve" in call.data:
            if call.data["curve"] not in CURVE_OPTIONS:
                raise HomeAssistantError(f"Invalid curve: {call.data['curve']}")
            updated["curve"] = call.data["curve"]
        if "weight" in call.data:
            updated["weight"] = float(call.data["weight"])
        if "invert" in call.data:
            updated["invert"] = bool(call.data["invert"])
        if "enabled" in call.data:
            updated["enabled"] = bool(call.data["enabled"])
        if updated["min"] >= updated["max"]:
            raise HomeAssistantError("min must be less than max")
        new_list.append(updated)
    if not found:
        raise HomeAssistantError(f"No modulator with id {mid}")
    await coord.async_save_modulators(new_list)
    _LOGGER.info("Updated modulator %s", mid)


async def _async_remove(call: ServiceCall) -> None:
    coord = _coordinator(call.hass)
    mods = modulators_from_options(dict(coord.entry.options))
    mid = (call.data.get("id") or "").strip() or None
    eid = _normalize_entity(call.data.get("entity_id")) if call.data.get("entity_id") else None
    if not mid and not eid:
        raise HomeAssistantError("Provide id or entity_id")

    before = len(mods)
    if mid:
        new_list = [m for m in mods if m["id"] != mid]
    else:
        new_list = [m for m in mods if m["entity_id"] != eid]
    if len(new_list) == before:
        raise HomeAssistantError("Modulator not found")
    await coord.async_save_modulators(new_list)
    _LOGGER.info("Removed modulator (id=%s entity_id=%s)", mid, eid)


async def _async_set_enabled(call: ServiceCall) -> None:
    coord = _coordinator(call.hass)
    mods = modulators_from_options(dict(coord.entry.options))
    mid = str(call.data["id"]).strip()
    enabled = bool(call.data["enabled"])
    found = False
    new_list = []
    for m in mods:
        if m["id"] == mid:
            found = True
            updated = dict(m)
            updated["enabled"] = enabled
            new_list.append(updated)
        else:
            new_list.append(m)
    if not found:
        raise HomeAssistantError(f"No modulator with id {mid}")
    await coord.async_save_modulators(new_list)
    _LOGGER.info("Modulator %s enabled=%s", mid, enabled)


async def async_setup_services(hass: HomeAssistant) -> None:
    hass.services.async_register(DOMAIN, SERVICE_ADD, _async_add)
    hass.services.async_register(DOMAIN, SERVICE_UPDATE, _async_update)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE, _async_remove)
    hass.services.async_register(DOMAIN, SERVICE_SET_ENABLED, _async_set_enabled)


async def async_unload_services(hass: HomeAssistant) -> None:
    for name in (SERVICE_ADD, SERVICE_UPDATE, SERVICE_REMOVE, SERVICE_SET_ENABLED):
        if hass.services.has_service(DOMAIN, name):
            hass.services.async_remove(DOMAIN, name)