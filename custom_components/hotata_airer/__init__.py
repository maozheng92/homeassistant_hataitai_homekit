"""Hotata Airer D10-ZM helper for Home Assistant.

Wraps the Xiaomi Home cover for 好太太晾衣架 D10-ZM and inverts
up/down commands, open/close state, and position percentage so HomeKit
and the Home Assistant cover UI match the physical rack.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_HIDE_SOURCE, DEFAULT_HIDE_SOURCE, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]


def _source_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Resolve the wrapped Xiaomi cover entity id."""
    stored = entry.data.get(CONF_ENTITY_ID) or entry.options.get(CONF_ENTITY_ID)
    registry = er.async_get(hass)
    try:
        return er.async_validate_entity_id(registry, stored)
    except Exception:  # noqa: BLE001 - keep setup resilient to stale ids
        return stored


def _hide_source(hass: HomeAssistant, entity_id: str) -> None:
    """Hide the Xiaomi cover so HomeKit only sees the inverted entity."""
    registry = er.async_get(hass)
    source = registry.async_get(entity_id)
    if source is None or source.hidden:
        return
    registry.async_update_entity(
        entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
    )


def _copy_expose_settings(
    hass: HomeAssistant, source_entity_id: str, target_entity_id: str
) -> None:
    """Move HomeKit / assistant expose flags from the Xiaomi cover to ours."""
    try:
        from homeassistant.components.homeassistant import exposed_entities
    except ImportError:
        return

    try:
        expose_settings = exposed_entities.async_get_entity_settings(
            hass, source_entity_id
        )
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Unable to read expose settings for %s", source_entity_id)
        return

    for assistant, settings in expose_settings.items():
        should_expose = settings.get("should_expose")
        if should_expose is None:
            continue
        try:
            exposed_entities.async_expose_entity(
                hass, assistant, target_entity_id, should_expose
            )
            exposed_entities.async_expose_entity(
                hass, assistant, source_entity_id, False
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Unable to copy expose settings for %s", assistant)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    entity_id = _source_entity_id(hass, entry)
    hide_source = entry.data.get(CONF_HIDE_SOURCE, DEFAULT_HIDE_SOURCE)

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_ENTITY_ID: entity_id,
        CONF_HIDE_SOURCE: hide_source,
    }

    if hide_source:
        _hide_source(hass, entity_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Restore the wrapped Xiaomi cover when this helper is removed."""
    registry = er.async_get(hass)
    stored = entry.data.get(CONF_ENTITY_ID) or entry.options.get(CONF_ENTITY_ID)
    try:
        entity_id = er.async_validate_entity_id(registry, stored)
    except Exception:  # noqa: BLE001
        return

    source = registry.async_get(entity_id)
    if source is None:
        return
    if source.hidden_by == er.RegistryEntryHider.INTEGRATION:
        registry.async_update_entity(entity_id, hidden_by=None)
