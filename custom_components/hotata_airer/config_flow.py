"""Config flow for Hotata Airer D10-ZM."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er, selector

from .const import (
    CONF_HIDE_SOURCE,
    DEFAULT_HIDE_SOURCE,
    DOMAIN,
    XIAOMI_HOME_DOMAIN,
)
from .discovery import is_d10zm_device, iter_xiaomi_covers


def _discover_source_covers(hass: HomeAssistant) -> tuple[list[str], list[str]]:
    """Return (d10zm covers, other Xiaomi covers)."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    d10zm: list[str] = []
    others: list[str] = []

    for entry in iter_xiaomi_covers(entity_registry.entities.values()):
        device = (
            device_registry.async_get(entry.device_id) if entry.device_id else None
        )
        if is_d10zm_device(
            model=getattr(device, "model", None),
            name=" ".join(
                filter(
                    None,
                    [
                        getattr(device, "name_by_user", None),
                        getattr(device, "name", None),
                        entry.original_name,
                        entry.name,
                    ],
                )
            ),
            unique_id=entry.unique_id,
            identifiers=getattr(device, "identifiers", None),
        ):
            d10zm.append(entry.entity_id)
        else:
            others.append(entry.entity_id)
    return d10zm, others


class HotataAirerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the inverted D10-ZM cover."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Select the Xiaomi Home cover to invert."""
        errors: dict[str, str] = {}
        d10zm, others = _discover_source_covers(self.hass)

        if user_input is not None:
            entity_id = user_input[CONF_ENTITY_ID]
            registry = er.async_get(self.hass)
            source = registry.async_get(entity_id)
            unique_id = (
                f"{DOMAIN}_{source.unique_id}"
                if source and source.unique_id
                else f"{DOMAIN}_{entity_id}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            title = _entry_title(self.hass, entity_id)
            return self.async_create_entry(
                title=title,
                data={
                    CONF_ENTITY_ID: entity_id,
                    CONF_HIDE_SOURCE: user_input.get(
                        CONF_HIDE_SOURCE, DEFAULT_HIDE_SOURCE
                    ),
                },
            )

        if not d10zm and not others:
            return self.async_abort(reason="no_xiaomi_covers")

        suggested = d10zm[0] if d10zm else others[0]
        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID, default=suggested): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="cover",
                        integration=XIAOMI_HOME_DOMAIN,
                    )
                ),
                vol.Optional(
                    CONF_HIDE_SOURCE, default=DEFAULT_HIDE_SOURCE
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "model": "好太太晾衣架 D10-ZM",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return HotataAirerOptionsFlow(config_entry)


class HotataAirerOptionsFlow(config_entries.OptionsFlow):
    """Allow toggling whether the Xiaomi cover stays hidden."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Manage options."""
        if user_input is not None:
            hide_source = user_input[CONF_HIDE_SOURCE]
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={**self._config_entry.data, CONF_HIDE_SOURCE: hide_source},
            )
            _apply_hide_source(
                self.hass,
                self._config_entry.data.get(CONF_ENTITY_ID),
                hide_source,
            )
            return self.async_create_entry(title="", data=user_input)

        hide_source = self._config_entry.data.get(
            CONF_HIDE_SOURCE, DEFAULT_HIDE_SOURCE
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HIDE_SOURCE, default=hide_source
                    ): selector.BooleanSelector()
                }
            ),
        )


def _apply_hide_source(
    hass: HomeAssistant, entity_id: str | None, hide_source: bool
) -> None:
    """Hide or restore the Xiaomi cover according to the option."""
    if not entity_id:
        return
    registry = er.async_get(hass)
    try:
        entity_id = er.async_validate_entity_id(registry, entity_id)
    except Exception:  # noqa: BLE001
        return
    source = registry.async_get(entity_id)
    if source is None:
        return
    if hide_source and not source.hidden:
        registry.async_update_entity(
            entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
        )
    elif (
        not hide_source and source.hidden_by == er.RegistryEntryHider.INTEGRATION
    ):
        registry.async_update_entity(entity_id, hidden_by=None)


def _entry_title(hass: HomeAssistant, entity_id: str) -> str:
    """Use the Xiaomi device name for the config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    entity = entity_registry.async_get(entity_id)
    if entity and entity.device_id:
        device = device_registry.async_get(entity.device_id)
        if device:
            return device.name_by_user or device.name or "好太太晾衣架 D10-ZM"
    state = hass.states.get(entity_id)
    if state and state.name:
        return state.name
    return "好太太晾衣架 D10-ZM"
