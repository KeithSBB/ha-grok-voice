"""Config flow for Grok Voice."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
    CONF_TOKEN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_TOKEN): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    token = data[CONF_TOKEN]

    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}/health"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 401 or resp.status == 403:
                raise ValueError("invalid_auth")
            if resp.status != 200:
                # Endpoint may not exist yet during early scaffolding; still accept
                # the connection parameters so the user can finish setup.
                _LOGGER.warning(
                    "Health check returned %s – continuing setup (microservice may need /health)",
                    resp.status,
                )
            # Optionally parse body later when /health is implemented
    except aiohttp.ClientError as err:
        _LOGGER.error("Cannot connect to Grok Voice service: %s", err)
        raise ValueError("cannot_connect") from err

    return {"title": f"Grok Voice ({host}:{port})"}


class GrokVoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grok Voice."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError as err:
                if str(err) == "cannot_connect":
                    errors["base"] = "cannot_connect"
                elif str(err) == "invalid_auth":
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "unknown"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config validation")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
