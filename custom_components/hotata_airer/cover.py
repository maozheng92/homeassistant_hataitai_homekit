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
from .invert import (
    ACTION_CLOSE,
    ACTION_OPEN,
    ACTION_STOP,
    inverted_cover_snapshot,
    position_seek_action,
)

_SEEK_SERVICES = {
    ACTION_OPEN: SERVICE_CLOSE_COVER,
    ACTION_CLOSE: SERVICE_OPEN_COVER,
    ACTION_STOP: SERVICE_STOP_COVER,
}


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
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        self._requested_position: int | None = None
        self._source_has_set_position = False
        self._seek_in_flight = False
        self._last_seek_action: str | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to the Xiaomi cover and attach to the same device."""

        @callback
        def _on_source_change(event: Event | None = None) -> None:
            self._apply_source_state()
            self.async_write_ha_state()
            self._schedule_seek_followup()

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
        self._source_has_set_position = bool(snapshot["source_has_set_position"])
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

    @callback
    def _schedule_seek_followup(self) -> None:
        """Stop or keep moving after Xiaomi reports a new position."""
        if self._source_has_set_position or self._seek_in_flight:
            return
        action = position_seek_action(
            self._attr_current_cover_position,
            self._requested_position,
            is_opening=bool(self._attr_is_opening),
            is_closing=bool(self._attr_is_closing),
        )
        if action is None or action == self._last_seek_action:
            return
        self._seek_in_flight = True
        self.hass.async_create_task(self._async_run_seek_action(action))

    async def _async_run_seek_action(self, action: str) -> None:
        """Send one motor command, then re-evaluate the seek."""
        self._last_seek_action = action
        if action == ACTION_STOP:
            self._requested_position = None
        try:
            await self._async_call_source(_SEEK_SERVICES[action])
        finally:
            self._seek_in_flight = False
            if self._requested_position is not None:
                self._schedule_seek_followup()

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
        self._requested_position = None
        self._last_seek_action = ACTION_OPEN
        self._attr_is_opening = True
        self._attr_is_closing = False
        self._attr_is_closed = False
        self.async_write_ha_state()
        await self._async_call_source(SERVICE_CLOSE_COVER)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """下降 / close 发送给米家的上升键。"""
        self._requested_position = None
        self._last_seek_action = ACTION_CLOSE
        self._attr_is_opening = False
        self._attr_is_closing = True
        self.async_write_ha_state()
        await self._async_call_source(SERVICE_OPEN_COVER)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """暂停不反向。"""
        self._requested_position = None
        self._last_seek_action = ACTION_STOP
        self._attr_is_opening = False
        self._attr_is_closing = False
        self.async_write_ha_state()
        await self._async_call_source(SERVICE_STOP_COVER)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Show the HA percent slider; invert or emulate the move."""
        position = kwargs.get(ATTR_POSITION)
        if position is None:
            return
        target = max(0, min(100, int(position)))
        current = self._attr_current_cover_position
        if current is not None:
            self._attr_is_opening = target > current
            self._attr_is_closing = target < current
            self._attr_is_closed = False
            self.async_write_ha_state()

        if self._source_has_set_position:
            self._requested_position = None
            await self._async_call_source(
                SERVICE_SET_COVER_POSITION,
                {ATTR_POSITION: 100 - target},
            )
            return

        self._requested_position = target
        self._last_seek_action = None
        action = position_seek_action(
            current,
            target,
            is_opening=False,
            is_closing=False,
        )
        if action is None:
            self._requested_position = None
            return
        self._seek_in_flight = True
        await self._async_run_seek_action(action)
