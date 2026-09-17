"""Inverted cover entity wrapping Xiaomi Home's D10-ZM airer."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
    DOMAIN as COVER_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import source_entity_id
from .invert import inverted_cover_snapshot


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the inverted D10-ZM cover."""
    async_add_entities(
        [InvertedHotataCover(hass, entry, source_entity_id(hass, entry))]
    )


class InvertedHotataCover(CoverEntity):
    """Cover that swaps Xiaomi Home up/down, state and percent."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:hanger"
    _attr_translation_key = "airer"
    _attr_name = None

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        source_entity_id: str,
    ) -> None:
        self.hass = hass
        self._source_entity_id = source_entity_id
        self._attr_unique_id = entry.entry_id
        self._attr_device_class = CoverDeviceClass.BLIND
        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to the Xiaomi cover and attach to the same device."""

        @callback
        def _on_source_change(event: Event | None = None) -> None:
            self._apply_source_state()
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity_id], _on_source_change
            )
        )
        self._apply_source_state()

        registry = er.async_get(self.hass)
        source = registry.async_get(self._source_entity_id)
        if source and source.device_id and registry.async_get(self.entity_id):
            registry.async_update_entity(
                self.entity_id, device_id=source.device_id
            )

    @callback
    def _apply_source_state(self) -> None:
        state = self.hass.states.get(self._source_entity_id)
        snapshot = inverted_cover_snapshot(
            None if state is None else state.state,
            None if state is None else dict(state.attributes),
        )
        self._attr_available = bool(snapshot["available"])
        self._attr_current_cover_position = snapshot["current_position"]
        self._attr_is_opening = snapshot["is_opening"]
        self._attr_is_closing = snapshot["is_closing"]
        self._attr_is_closed = snapshot["is_closed"]
        self._attr_supported_features = CoverEntityFeature(
            snapshot["supported_features"]
        )
        device_class = snapshot["device_class"]
        if isinstance(device_class, CoverDeviceClass):
            self._attr_device_class = device_class
        else:
            try:
                self._attr_device_class = CoverDeviceClass(device_class)
            except ValueError:
                self._attr_device_class = CoverDeviceClass.BLIND

    async def _async_call_source(self, service: str, data: dict[str, Any] | None = None) -> None:
        payload = {ATTR_ENTITY_ID: self._source_entity_id}
        if data:
            payload.update(data)
        await self.hass.services.async_call(
            COVER_DOMAIN,
            service,
            payload,
            blocking=True,
            context=self._context,
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """上升 / open 发送给米家的下降键。"""
        self._attr_is_opening = True
        self._attr_is_closing = False
        self._attr_is_closed = False
        self.async_write_ha_state()
        await self._async_call_source(SERVICE_CLOSE_COVER)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """下降 / close 发送给米家的上升键。"""
        self._attr_is_opening = False
        self._attr_is_closing = True
        self.async_write_ha_state()
        await self._async_call_source(SERVICE_OPEN_COVER)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """暂停不反向。"""
        self._attr_is_opening = False
        self._attr_is_closing = False
        self.async_write_ha_state()
        await self._async_call_source(SERVICE_STOP_COVER)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """把目标百分比取反后再发给米家。"""
        position = kwargs.get(ATTR_POSITION)
        if position is None:
            return
        target = int(position)
        inverted = max(0, min(100, 100 - target))
        current = self._attr_current_cover_position
        if current is not None:
            self._attr_is_opening = target > current
            self._attr_is_closing = target < current
            self._attr_is_closed = False
            self.async_write_ha_state()
        await self._async_call_source(
            SERVICE_SET_COVER_POSITION, {ATTR_POSITION: inverted}
        )
