"""DataUpdateCoordinator for Grok Voice."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientSession, ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .personality import modulators_from_options

_LOGGER = logging.getLogger(__name__)


class GrokVoiceDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Grok Voice data and push personality config/states."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
    ) -> None:
        self.entry = entry
        self.session = session
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.token = entry.data[CONF_TOKEN]
        self.personality_tracker = None  # set by __init__.py

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def get_modulators(self) -> list[dict[str, Any]]:
        return modulators_from_options(dict(self.entry.options))

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "status": "unknown",
            "system_prompt": "",
            "voice": "rex",
            "model": "grok-voice-latest",
            "conversation_timeout_seconds": 10,
            "conversation_persistence_seconds": 300,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "active_satellites": 0,
            "personality_sync": "never",
            "personality_modulator_count": 0,
        }

        tracker = self.personality_tracker
        if tracker is not None:
            data["personality_sync"] = tracker.last_sync_status
            data["personality_last_sync_at"] = tracker.last_sync_at
            data["personality_last_error"] = tracker.last_error

        data["personality_modulator_count"] = len(
            [m for m in self.get_modulators() if m.get("enabled", True)]
        )

        try:
            async with self.session.get(
                f"{self.base_url}/health",
                headers=self._headers(),
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    health = await resp.json()
                    data["status"] = health.get("status", "online")
                    data["active_satellites"] = health.get("active_satellites", 0)
                elif resp.status in (401, 403):
                    raise UpdateFailed("Authentication failed")
                else:
                    data["status"] = f"http_{resp.status}"

            try:
                async with self.session.get(
                    f"{self.base_url}/config",
                    headers=self._headers(),
                    timeout=10,
                ) as resp:
                    if resp.status == 200:
                        cfg = await resp.json()
                        data.update(
                            {
                                "system_prompt": cfg.get("system_prompt", data["system_prompt"]),
                                "voice": cfg.get("voice", data["voice"]),
                                "model": cfg.get("model", data["model"]),
                                "conversation_timeout_seconds": cfg.get(
                                    "conversation_timeout_seconds",
                                    data["conversation_timeout_seconds"],
                                ),
                                "conversation_persistence_seconds": cfg.get(
                                    "conversation_persistence_seconds",
                                    data["conversation_persistence_seconds"],
                                ),
                            }
                        )
            except ClientError:
                _LOGGER.debug("/config not available")

            try:
                async with self.session.get(
                    f"{self.base_url}/usage",
                    headers=self._headers(),
                    timeout=10,
                ) as resp:
                    if resp.status == 200:
                        usage = await resp.json()
                        data.update(
                            {
                                "input_tokens": usage.get("input_tokens", 0),
                                "output_tokens": usage.get("output_tokens", 0),
                                "estimated_cost": usage.get("estimated_cost", 0.0),
                            }
                        )
            except ClientError:
                _LOGGER.debug("/usage not available")

        except ClientError as err:
            raise UpdateFailed(f"Error communicating with Grok Voice service: {err}") from err

        return data

    async def async_set_config(self, key: str, value: Any) -> None:
        payload = {key: value}
        try:
            async with self.session.put(
                f"{self.base_url}/config",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
                timeout=10,
            ) as resp:
                if resp.status not in (200, 204):
                    text = await resp.text()
                    raise UpdateFailed(f"Failed to update config: HTTP {resp.status} – {text}")
        except ClientError as err:
            raise UpdateFailed(f"Error updating config: {err}") from err
        await self.async_request_refresh()

    async def async_push_personality_modulators(self, modulators: list[dict[str, Any]]) -> None:
        await self.async_set_config("personality_modulators", modulators)

    async def async_post_personality_states(
        self, states: dict[str, float], timestamp: str
    ) -> None:
        try:
            async with self.session.post(
                f"{self.base_url}/personality/states",
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"states": states, "timestamp": timestamp},
                timeout=10,
            ) as resp:
                if resp.status not in (200, 204):
                    text = await resp.text()
                    raise UpdateFailed(
                        f"Failed to post personality states: HTTP {resp.status} – {text}"
                    )
        except ClientError as err:
            raise UpdateFailed(f"Error posting personality states: {err}") from err