"""Invert Xiaomi Home airer cover semantics for HomeKit/HA.

Xiaomi Home maps 好太太 D10-ZM (`hotata.airer.d10zm`) as a cover:

- motor ``up`` (上升) → HA ``open`` / HomeKit up
- motor ``down`` (下降) → HA ``close`` / HomeKit down
- position 0 → closed, 100 → open

On this device those mappings are reversed. This helper swaps open/close
commands, opening/closing motion, the closed state, and the 0–100 position.
"""

from __future__ import annotations

from typing import Any

STATE_OPEN = "open"
STATE_CLOSED = "closed"
STATE_OPENING = "opening"
STATE_CLOSING = "closing"
STATE_UNAVAILABLE = "unavailable"
STATE_UNKNOWN = "unknown"

ATTR_CURRENT_POSITION = "current_position"
ATTR_SUPPORTED_FEATURES = "supported_features"

# CoverEntityFeature bits (stable across Home Assistant versions).
FEATURE_OPEN = 1
FEATURE_CLOSE = 2
FEATURE_SET_POSITION = 4
FEATURE_STOP = 8
INVERTIBLE_FEATURES = (
    FEATURE_OPEN | FEATURE_CLOSE | FEATURE_SET_POSITION | FEATURE_STOP
)


def invert_position(position: int | float | None) -> int | None:
    """Return 100 - position, clamped to 0–100."""
    if position is None:
        return None
    try:
        value = int(round(float(position)))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, 100 - value))


def invert_motion(
    source_state: str | None,
) -> tuple[bool, bool]:
    """Swap opening and closing reported by the Xiaomi cover.

    Returns ``(is_opening, is_closing)`` for the inverted entity.
    """
    if source_state == STATE_OPENING:
        return False, True
    if source_state == STATE_CLOSING:
        return True, False
    return False, False


def invert_is_closed(
    source_state: str | None,
    inverted_position: int | None,
) -> bool | None:
    """Return whether the inverted cover should report closed.

    Position 0 is closed. After inversion that is source position 100.
    Without a position, an ``open`` source is treated as closed and a
    ``closed`` source as open.
    """
    if inverted_position is not None:
        return inverted_position == 0
    if source_state == STATE_CLOSED:
        return False
    if source_state == STATE_OPEN:
        return True
    if source_state in {STATE_OPENING, STATE_CLOSING}:
        return False
    return None


def invert_supported_features(features: int | None) -> int:
    """Keep only open/close/stop/set-position bits from the source cover."""
    if features is None:
        return FEATURE_OPEN | FEATURE_CLOSE | FEATURE_STOP
    return int(features) & INVERTIBLE_FEATURES


def inverted_cover_snapshot(source_state: str | None, attributes: dict[str, Any] | None) -> dict[str, Any]:
    """Build inverted cover attributes from a Xiaomi Home cover state."""
    attrs = attributes or {}
    source_position = attrs.get(ATTR_CURRENT_POSITION)
    inverted_pos = invert_position(source_position)
    is_opening, is_closing = invert_motion(source_state)
    unavailable = source_state in {None, STATE_UNAVAILABLE, STATE_UNKNOWN}

    return {
        "available": not unavailable,
        "current_position": inverted_pos,
        "is_opening": is_opening if not unavailable else None,
        "is_closing": is_closing if not unavailable else None,
        "is_closed": invert_is_closed(source_state, inverted_pos) if not unavailable else None,
        "supported_features": invert_supported_features(attrs.get(ATTR_SUPPORTED_FEATURES)),
        "device_class": attrs.get("device_class") or "blind",
    }


def inverted_service_for_open() -> str:
    """HA open (上升) must call Xiaomi close (which is physically 上升 after swap)."""
    return "close_cover"


def inverted_service_for_close() -> str:
    """HA close (下降) must call Xiaomi open."""
    return "open_cover"
