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

_LOGGER = logging.getLogger(__name__)


class GrokVoiceDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Grok Voice data from the microservice."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
    ) -> None:
        """Initialize."""
        self.entry = entry
        self.session = session
        self.host = entry.data[CONF_HOST]
        self.port = entry.data[CONF_PORT]
        self.token = entry.data[CONF_TOKEN]

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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from /health, /config and /usage.

        Until the microservice implements these endpoints the coordinator
        returns a safe placeholder dict so entities can still be created.
        """
        data: dict[str, Any] = {
            "status": "unknown",
            "system_prompt": "",
            "voice": "rex",
            "model": "grok-voice-think-fast-1.0",
            "conversation_timeout_seconds": 10,
            "conversation_persistence_seconds": 300,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "active_satellites": 0,
        }

        try:
            # Health
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

            # Config (optional until implemented)
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
                _LOGGER.debug(" /config not available yet")

            # Usage (optional until implemented)
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
                _LOGGER.debug("/usage not available yet")

        except ClientError as err:
            raise UpdateFailed(f"Error communicating with Grok Voice service: {err}") from err

        return data

    async def async_set_config(self, key: str, value: Any) -> None:
        """Push a single config key to the microservice (PUT /config)."""
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

        # Force a refresh so entities see the new value
        await self.async_request_refresh()
