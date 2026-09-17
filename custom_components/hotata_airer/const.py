"""Constants for the Hotata Airer D10-ZM integration."""

from __future__ import annotations

DOMAIN = "hotata_airer"
XIAOMI_HOME_DOMAIN = "xiaomi_home"
MANUFACTURER = "HOTATA"
MODEL_D10ZM = "D10-ZM"
INVERTED_SUFFIX = "（反向）"

# Xiaomi Home maps this model as a cover/blind. Buttons, open/close
# state and position percent are inverted relative to HA covers.
MODEL_MARKERS = (
    "hotata.airer.d10zm",
    "d10zm",
    "d10-zm",
)


def inverted_device_name(source_name: str | None) -> str:
    """Name the new device so it is distinct from the Xiaomi original."""
    name = (source_name or "").strip() or "好太太晾衣架 D10-ZM"
    if "反向" in name:
        return name
    return f"{name}{INVERTED_SUFFIX}"
