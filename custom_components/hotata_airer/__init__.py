"""Hotata Airer D10-ZM integration for Home Assistant.

Creates a device that wraps the Xiaomi Home cover for 好太太晾衣架 D10-ZM
and inverts up/down commands, open/close state, and position percentage.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.COVER]


def source_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Resolve the wrapped Xiaomi cover entity id."""
    stored = entry.data.get(CONF_ENTITY_ID) or entry.options.get(CONF_ENTITY_ID)
    registry = er.async_get(hass)
    try:
        return er.async_validate_entity_id(registry, stored)
    except Exception:  # noqa: BLE001 - keep setup resilient to stale ids
        return stored


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_ENTITY_ID: source_entity_id(hass, entry),
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
