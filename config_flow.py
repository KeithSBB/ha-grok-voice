"""Config flow for Grok Voice."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ASPECT_OPTIONS,
    CONF_PERSONALITY_MODULATORS,
    CONF_SYSTEM_PROMPT,
    CONF_TOKEN,
    CURVE_OPTIONS,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
    SYSTEM_PROMPT_MAX_LENGTH,
)
from .personality import modulators_from_options

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_TOKEN): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    host = data[CONF_HOST]
    port = data[CONF_PORT]
    token = data[CONF_TOKEN]
    session = async_get_clientsession(hass)
    url = f"http://{host}:{port}/health"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status in (401, 403):
                raise ValueError("invalid_auth")
            if resp.status != 200:
                _LOGGER.warning("Health check returned %s – continuing setup", resp.status)
    except aiohttp.ClientError as err:
        _LOGGER.error("Cannot connect to Grok Voice service: %s", err)
        raise ValueError("cannot_connect") from err
    return {"title": f"Grok Voice ({host}:{port})"}


class GrokVoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return GrokVoiceOptionsFlow()


class GrokVoiceOptionsFlow(config_entries.OptionsFlow):
    """Options: system prompt + personality modulators."""

    def __init__(self) -> None:
        self._edit_id: str | None = None
        self._selected_id: str | None = None
        self._modulators: list[dict[str, Any]] | None = None

    def _mods(self) -> list[dict[str, Any]]:
        if self._modulators is None:
            self._modulators = modulators_from_options(dict(self.config_entry.options))
        return list(self._modulators)

    def _coordinator(self):
        return self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)

    def _options_snapshot(self) -> dict[str, Any]:
        """Build full options dict from entry + in-memory modulators."""
        opts = dict(self.config_entry.options)
        if self._modulators is not None:
            opts[CONF_PERSONALITY_MODULATORS] = self._modulators
        return opts

    async def _persist_modulators(self, modulators: list[dict[str, Any]]) -> str | None:
        """Save to entry options and push to microservice. Returns error key or None."""
        self._modulators = modulators
        opts = dict(self.config_entry.options)
        opts[CONF_PERSONALITY_MODULATORS] = modulators
        self.hass.config_entries.async_update_entry(self.config_entry, options=opts)

        coord = self._coordinator()
        if coord is None:
            return None
        try:
            await coord.async_push_personality_modulators(modulators)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Failed to push personality_modulators: %s", err)
            return "cannot_connect"
        if coord.personality_tracker:
            await coord.personality_tracker.async_rebuild()
        return None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            next_step = user_input.get("next_step")
            if next_step == "prompt":
                return await self.async_step_prompt()
            if next_step == "modulators":
                return await self.async_step_modulators()
            # Done — commit in-memory list into the options entry result
            return self.async_create_entry(title="", data=self._options_snapshot())

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("next_step", default="modulators"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "prompt", "label": "System Prompt"},
                                {"value": "modulators", "label": "Personality Modulators"},
                                {"value": "done", "label": "Done / Save & Close"},
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_prompt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        current = self.config_entry.options.get(CONF_SYSTEM_PROMPT, "")
        coord = self._coordinator()
        if coord and coord.data and coord.data.get("system_prompt"):
            current = coord.data["system_prompt"]

        if user_input is not None:
            prompt = (user_input.get(CONF_SYSTEM_PROMPT) or "").strip()
            if len(prompt) > SYSTEM_PROMPT_MAX_LENGTH:
                errors["base"] = "prompt_too_long"
            else:
                if coord is not None:
                    try:
                        await coord.async_set_config(CONF_SYSTEM_PROMPT, prompt)
                    except Exception as err:  # pylint: disable=broad-except
                        _LOGGER.error("Failed to update system prompt: %s", err)
                        errors["base"] = "cannot_connect"
                if not errors:
                    opts = self._options_snapshot()
                    opts[CONF_SYSTEM_PROMPT] = prompt
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, options=opts
                    )
                    return await self.async_step_init()

        return self.async_show_form(
            step_id="prompt",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SYSTEM_PROMPT, default=current
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            multiline=True,
                            type=selector.TextSelectorType.TEXT,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_modulators(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """List each modulator once; Add or select one to manage."""
        mods = self._mods()
        if user_input is not None:
            choice = user_input.get("choice")
            if choice == "add":
                self._edit_id = None
                return await self.async_step_modulator_form()
            if choice == "back":
                return await self.async_step_init()
            if choice and choice.startswith("mod:"):
                self._selected_id = choice[4:]
                return await self.async_step_modulator_action()
            return await self.async_step_init()

        options = [{"value": "add", "label": "➕ Add new modulator"}]
        for m in mods:
            enabled = "✓" if m.get("enabled", True) else "✗"
            options.append(
                {
                    "value": f"mod:{m['id']}",
                    "label": f"{enabled} {m['entity_id']} → {m['aspect']}",
                }
            )
        options.append({"value": "back", "label": "← Back"})

        return self.async_show_form(
            step_id="modulators",
            data_schema=vol.Schema(
                {
                    vol.Required("choice", default="add"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={"count": str(len(mods))},
        )

    async def async_step_modulator_action(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """After picking one modulator: Edit or Delete."""
        mods = self._mods()
        selected = next((m for m in mods if m["id"] == self._selected_id), None)
        if selected is None:
            return await self.async_step_modulators()

        if user_input is not None:
            action = user_input.get("action")
            if action == "edit":
                self._edit_id = self._selected_id
                return await self.async_step_modulator_form()
            if action == "delete":
                new_list = [m for m in mods if m["id"] != self._selected_id]
                err = await self._persist_modulators(new_list)
                self._selected_id = None
                if err:
                    return self.async_show_form(
                        step_id="modulator_action",
                        data_schema=vol.Schema(
                            {
                                vol.Required("action", default="edit"): selector.SelectSelector(
                                    selector.SelectSelectorConfig(
                                        options=[
                                            {"value": "edit", "label": "Edit"},
                                            {"value": "delete", "label": "Delete"},
                                            {"value": "back", "label": "← Back"},
                                        ],
                                        mode=selector.SelectSelectorMode.LIST,
                                    )
                                )
                            }
                        ),
                        errors={"base": err},
                        description_placeholders={
                            "entity": selected["entity_id"],
                            "aspect": selected["aspect"],
                        },
                    )
                return await self.async_step_modulators()
            # back
            self._selected_id = None
            return await self.async_step_modulators()

        return self.async_show_form(
            step_id="modulator_action",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="edit"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "edit", "label": "✏️ Edit this modulator"},
                                {"value": "delete", "label": "🗑️ Delete this modulator"},
                                {"value": "back", "label": "← Back to list"},
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
            description_placeholders={
                "entity": selected["entity_id"],
                "aspect": selected["aspect"],
            },
        )

    async def async_step_modulator_form(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        mods = self._mods()
        existing = next((m for m in mods if m["id"] == self._edit_id), None) if self._edit_id else None

        if user_input is not None:
            try:
                mn = float(user_input["min"])
                mx = float(user_input["max"])
            except (TypeError, ValueError):
                errors["base"] = "invalid_range"
                mn, mx = 0.0, 1.0
            else:
                if mn >= mx:
                    errors["base"] = "invalid_range"

            eid = user_input.get("entity_id")
            if hasattr(eid, "entity_id"):
                eid = eid.entity_id
            eid = str(eid or "").strip()
            if not eid:
                errors["base"] = "missing_entity"

            if not errors:
                mid = existing["id"] if existing else str(uuid.uuid4())
                new_mod = {
                    "id": mid,
                    "entity_id": eid,
                    "aspect": user_input["aspect"],
                    "min": mn,
                    "max": mx,
                    "curve": user_input.get("curve") or "linear",
                    "weight": float(user_input.get("weight", 1.0)),
                    "invert": bool(user_input.get("invert", False)),
                    "enabled": bool(user_input.get("enabled", True)),
                }
                if existing:
                    new_list = [new_mod if m["id"] == mid else m for m in mods]
                else:
                    new_list = mods + [new_mod]
                err = await self._persist_modulators(new_list)
                if err:
                    errors["base"] = err
                else:
                    self._edit_id = None
                    self._selected_id = None
                    return await self.async_step_modulators()

        defaults = existing or {
            "entity_id": None,
            "aspect": "warmth",
            "min": 0.0,
            "max": 100.0,
            "curve": "linear",
            "weight": 1.0,
            "invert": False,
            "enabled": True,
        }

        entity_default = defaults.get("entity_id") or vol.UNDEFINED
        schema_dict: dict[Any, Any] = {
            vol.Required("entity_id", default=entity_default): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Required("aspect", default=defaults.get("aspect", "warmth")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": a, "label": a.capitalize()} for a in ASPECT_OPTIONS
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required("min", default=float(defaults.get("min", 0))): vol.Coerce(float),
            vol.Required("max", default=float(defaults.get("max", 100))): vol.Coerce(float),
            vol.Required("curve", default=defaults.get("curve", "linear")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=CURVE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required("weight", default=float(defaults.get("weight", 1.0))): vol.All(
                vol.Coerce(float), vol.Range(min=0.0, max=2.0)
            ),
            vol.Required("invert", default=bool(defaults.get("invert", False))): bool,
            vol.Required("enabled", default=bool(defaults.get("enabled", True))): bool,
        }

        return self.async_show_form(
            step_id="modulator_form",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def _persist_modulators(self, modulators: list[dict[str, Any]]) -> None:
        await self._save_options({CONF_PERSONALITY_MODULATORS: modulators})
        coord = self._coordinator()
        if coord is not None:
            try:
                await coord.async_push_personality_modulators(modulators)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Failed to push personality_modulators: %s", err)
            if coord.personality_tracker:
                await coord.personality_tracker.async_rebuild()