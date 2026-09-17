"""Invert Xiaomi Home airer cover semantics.

Xiaomi Home maps 好太太 D10-ZM (`hotata.airer.d10zm`) as a cover:

- motor ``up`` (上升) → HA ``open``
- motor ``down`` (下降) → HA ``close``
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
ALWAYS_ON_FEATURES = (
    FEATURE_OPEN | FEATURE_CLOSE | FEATURE_STOP | FEATURE_SET_POSITION
)

ACTION_OPEN = "open"
ACTION_CLOSE = "close"
ACTION_STOP = "stop"
POSITION_DEADZONE = 5


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
    """Expose open/close/stop plus a position slider.

    D10-ZM has no writable target-position, so Xiaomi Home often omits
    ``SET_POSITION``. The helper still advertises it and emulates the
    slider with motor up/down plus current-position feedback.
    """
    copied = 0 if features is None else int(features) & INVERTIBLE_FEATURES
    return copied | ALWAYS_ON_FEATURES


def source_has_set_position(features: int | None) -> bool:
    """Return True if the Xiaomi cover can take ``cover.set_cover_position``."""
    if not features:
        return False
    return bool(int(features) & FEATURE_SET_POSITION)


def position_seek_action(
    current: int | None,
    target: int | None,
    *,
    is_opening: bool = False,
    is_closing: bool = False,
    deadzone: int = POSITION_DEADZONE,
) -> str | None:
    """Choose the next inverted-cover motor action while seeking a percent.

    Returns ``open``, ``close``, ``stop``, or ``None`` to keep waiting.
    Targets 0 and 100 run to the mechanical end and are not auto-stopped
    at the deadzone, so the rack can fully raise or lower.
    """
    if target is None:
        return None
    try:
        target = max(0, min(100, int(target)))
    except (TypeError, ValueError):
        return None

    if current is None:
        if target >= 50:
            return None if is_opening else ACTION_OPEN
        return None if is_closing else ACTION_CLOSE

    if target >= 100:
        if current >= 100:
            return ACTION_STOP if (is_opening or is_closing) else None
        return None if is_opening else ACTION_OPEN
    if target <= 0:
        if current <= 0:
            return ACTION_STOP if (is_opening or is_closing) else None
        return None if is_closing else ACTION_CLOSE

    if abs(current - target) <= deadzone:
        return ACTION_STOP if (is_opening or is_closing) else None
    if target > current:
        return None if is_opening else ACTION_OPEN
    return None if is_closing else ACTION_CLOSE


def inverted_cover_snapshot(source_state: str | None, attributes: dict[str, Any] | None) -> dict[str, Any]:
    """Build inverted cover attributes from a Xiaomi Home cover state."""
    attrs = attributes or {}
    source_position = attrs.get(ATTR_CURRENT_POSITION)
    inverted_pos = invert_position(source_position)
    is_opening, is_closing = invert_motion(source_state)
    unavailable = source_state in {None, STATE_UNAVAILABLE, STATE_UNKNOWN}

    raw_features = attrs.get(ATTR_SUPPORTED_FEATURES)
    return {
        "available": not unavailable,
        "current_position": inverted_pos,
        "is_opening": is_opening if not unavailable else None,
        "is_closing": is_closing if not unavailable else None,
        "is_closed": invert_is_closed(source_state, inverted_pos) if not unavailable else None,
        "supported_features": invert_supported_features(raw_features),
        "source_has_set_position": source_has_set_position(raw_features),
        "device_class": attrs.get("device_class") or "blind",
    }


def inverted_service_for_open() -> str:
    """HA open (上升) must call Xiaomi close (which is physically 上升 after swap)."""
    return "close_cover"


def inverted_service_for_close() -> str:
    """HA close (下降) must call Xiaomi open."""
    return "open_cover"
