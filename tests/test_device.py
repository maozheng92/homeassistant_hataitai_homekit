"""Tests for device via_device_id linking."""

from __future__ import annotations

import sys
import types
import unittest
from types import SimpleNamespace

from test_invert import load

_HA_STUBBED = False


def _install_homeassistant_stubs() -> None:
    global _HA_STUBBED
    if _HA_STUBBED:
        return

    ha = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    helpers = types.ModuleType("homeassistant.helpers")
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    device_registry.DeviceInfo = dict

    class DeviceRegistry:
        def async_get_or_create(self, *, via_device_id=None, **kwargs):
            return SimpleNamespace(id="new", via_device_id=via_device_id)

    device_registry.DeviceRegistry = DeviceRegistry

    sys.modules.update(
        {
            "homeassistant": ha,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.device_registry": device_registry,
            "homeassistant.helpers.entity_registry": entity_registry,
        }
    )
    ha.config_entries = config_entries
    ha.core = core
    ha.helpers = helpers
    helpers.device_registry = device_registry
    helpers.entity_registry = entity_registry
    _HA_STUBBED = True


_install_homeassistant_stubs()
device = load("device")


class ViaFieldsTests(unittest.TestCase):
    def test_uses_via_device_id_on_current_ha(self) -> None:
        source = SimpleNamespace(
            id="xiaomi-device-1",
            identifiers={("xiaomi_home", "hotata.airer.d10zm")},
        )
        fields = device.via_fields_for_device(source)
        self.assertEqual(fields, {"via_device_id": "xiaomi-device-1"})
        self.assertNotIn("via_device", fields)

    def test_omits_link_without_source_device(self) -> None:
        self.assertEqual(device.via_fields_for_device(None), {})
        self.assertEqual(device.via_fields_for_device(SimpleNamespace(id=None)), {})

    def test_falls_back_to_via_device_on_old_ha(self) -> None:
        original = device.dr.DeviceRegistry.async_get_or_create

        def legacy_create(self, *, via_device=None, **kwargs):
            return SimpleNamespace(via_device=via_device)

        device.dr.DeviceRegistry.async_get_or_create = legacy_create
        try:
            source = SimpleNamespace(
                id="xiaomi-device-1",
                identifiers={("xiaomi_home", "hotata.airer.d10zm")},
            )
            fields = device.via_fields_for_device(source)
            self.assertEqual(
                fields, {"via_device": ("xiaomi_home", "hotata.airer.d10zm")}
            )
            self.assertNotIn("via_device_id", fields)
        finally:
            device.dr.DeviceRegistry.async_get_or_create = original


if __name__ == "__main__":
    unittest.main()
