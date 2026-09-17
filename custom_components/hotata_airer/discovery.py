"""Find Xiaomi Home 好太太 D10-ZM cover entities."""

from __future__ import annotations

from typing import Any

from .const import MODEL_MARKERS, XIAOMI_HOME_DOMAIN


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "").replace("_", "")


def is_d10zm_device(
    model: str | None = None,
    name: str | None = None,
    unique_id: str | None = None,
    identifiers: Any = None,
) -> bool:
    """Return True if the device looks like Hotata D10-ZM."""
    parts: list[str] = []
    for item in (model, name, unique_id):
        if item:
            parts.append(str(item))
    if identifiers:
        for ident in identifiers:
            if isinstance(ident, (tuple, list)):
                parts.extend(str(part) for part in ident)
            else:
                parts.append(str(ident))
    blob = _normalize(" ".join(parts))
    return any(_normalize(marker) in blob for marker in MODEL_MARKERS)


def iter_xiaomi_covers(entity_entries: Any) -> list[Any]:
    """Return enabled Xiaomi Home cover registry entries."""
    covers = []
    for entry in entity_entries:
        if entry.domain != "cover" or entry.disabled:
            continue
        if entry.platform != XIAOMI_HOME_DOMAIN:
            continue
        covers.append(entry)
    return covers
