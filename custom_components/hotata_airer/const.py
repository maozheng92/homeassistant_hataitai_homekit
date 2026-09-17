"""Constants for the Hotata Airer D10-ZM helper."""

from __future__ import annotations

DOMAIN = "hotata_airer"
XIAOMI_HOME_DOMAIN = "xiaomi_home"

# Xiaomi Home maps this model as a cover/blind. Buttons, open/close
# state and position percent are inverted relative to HomeKit/HA covers.
MODEL_MARKERS = (
    "hotata.airer.d10zm",
    "d10zm",
    "d10-zm",
)

CONF_HIDE_SOURCE = "hide_source"
DEFAULT_HIDE_SOURCE = True
