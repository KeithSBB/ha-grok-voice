"""Personality modulator state tracking and push to microservice."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from datetime import timedelta

from .const import CONF_PERSONALITY_MODULATORS

_LOGGER = logging.getLogger(__name__)


class PersonalityTracker:
    """Track HA entity states for enabled modulators and POST to microservice."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        get_modulators: Callable[[], list[dict[str, Any]]],
        post_states: Callable[[dict[str, float], str], Any],
        interval_seconds: int = 20,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._get_modulators = get_modulators
        self._post_states = post_states
        self._interval = interval_seconds
        self._unsub_state: Callable[[], None] | None = None
        self._unsub_interval: Callable[[], None] | None = None
        self._entity_ids: set[str] = set()
        self.last_sync_status: str = "never"
        self.last_sync_at: str | None = None
        self.last_error: str | None = None

    async def async_start(self) -> None:
        await self.async_rebuild()

    async def async_stop(self) -> None:
        self._unsubscribe()

    def _unsubscribe(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None

    async def async_rebuild(self) -> None:
        """Rebuild listeners from current modulator list and push config+states."""
        self._unsubscribe()
        mods = self._get_modulators()
        self._entity_ids = {
            m["entity_id"]
            for m in mods
            if m.get("enabled", True) and m.get("entity_id")
        }
        if self._entity_ids:
            self._unsub_state = async_track_state_change_event(
                self.hass,
                list(self._entity_ids),
                self._on_state_change,
            )
            self._unsub_interval = async_track_time_interval(
                self.hass,
                self._on_interval,
                timedelta(seconds=self._interval),
            )
            await self._async_push_states()
        else:
            self.last_sync_status = "idle"
            self.last_error = None

    @callback
    def _on_state_change(self, event: Event) -> None:
        self.hass.async_create_task(self._async_push_states())

    @callback
    def _on_interval(self, _now) -> None:
        self.hass.async_create_task(self._async_push_states())

    async def _async_push_states(self) -> None:
        if not self._entity_ids:
            return
        states: dict[str, float] = {}
        for eid in self._entity_ids:
            st = self.hass.states.get(eid)
            if st is None or st.state in ("unknown", "unavailable", "none", ""):
                continue
            try:
                states[eid] = float(st.state)
            except (TypeError, ValueError):
                continue
        ts = datetime.now(timezone.utc).isoformat()
        try:
            await self._post_states(states, ts)
            self.last_sync_status = "ok"
            self.last_sync_at = ts
            self.last_error = None
        except Exception as err:  # pylint: disable=broad-except
            self.last_sync_status = "error"
            self.last_error = str(err)
            _LOGGER.warning("Personality state push failed: %s", err)


def modulators_from_options(options: dict[str, Any]) -> list[dict[str, Any]]:
    raw = options.get(CONF_PERSONALITY_MODULATORS) or []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for m in raw:
        if not isinstance(m, dict):
            continue
        if not m.get("id") or not m.get("entity_id") or not m.get("aspect"):
            continue
        try:
            mn = float(m["min"])
            mx = float(m["max"])
        except (KeyError, TypeError, ValueError):
            continue
        if mn >= mx:
            continue
        out.append({
            "id": str(m["id"]),
            "entity_id": str(m["entity_id"]),
            "aspect": str(m["aspect"]),
            "min": mn,
            "max": mx,
            "curve": str(m.get("curve") or "linear"),
            "weight": float(m.get("weight", 1.0)),
            "invert": bool(m.get("invert", False)),
            "enabled": bool(m.get("enabled", True)),
        })
    return out