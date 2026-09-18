"""Device registry helpers for the inverted D10-ZM cover."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL_D10ZM, inverted_device_name


def device_info_for_source(
    hass: HomeAssistant, entry: ConfigEntry, source_entity_id: str
) -> DeviceInfo:
    """Create a standalone device for this integration, via the Xiaomi device."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    source = entity_registry.async_get(source_entity_id)

    name = inverted_device_name(entry.title)
    manufacturer = MANUFACTURER
    model = MODEL_D10ZM
    sw_version = None
    via_device: tuple[str, str] | None = None

    if source and source.device_id:
        device = device_registry.async_get(source.device_id)
        if device:
            name = inverted_device_name(
                device.name_by_user or device.name or entry.title
            )
            manufacturer = device.manufacturer or manufacturer
            model = device.model or model
            sw_version = device.sw_version
            if device.identifiers:
                ident = next(iter(device.identifiers))
                if (
                    isinstance(ident, tuple)
                    and len(ident) >= 2
                    and ident[0] != DOMAIN
                ):
                    via_device = (str(ident[0]), str(ident[1]))

    data: dict[str, Any] = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": name,
        "manufacturer": manufacturer,
        "model": model,
    }
    if sw_version:
        data["sw_version"] = sw_version
    if via_device:
        data["via_device"] = via_device
    return DeviceInfo(**data)


def async_register_device(
    hass: HomeAssistant, entry: ConfigEntry, source_entity_id: str
) -> dr.DeviceEntry:
    """Register this config entry as its own device, not a helper."""
    info = device_info_for_source(hass, entry, source_entity_id)
    kwargs: dict[str, Any] = {
        "config_entry_id": entry.entry_id,
        "identifiers": info["identifiers"],
        "name": info.get("name"),
        "manufacturer": info.get("manufacturer"),
        "model": info.get("model"),
    }
    if info.get("sw_version"):
        kwargs["sw_version"] = info["sw_version"]
    if info.get("via_device"):
        kwargs["via_device"] = info["via_device"]
    return dr.async_get(hass).async_get_or_create(**kwargs)
