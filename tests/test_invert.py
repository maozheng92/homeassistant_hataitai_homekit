"""Tests for Hotata D10-ZM cover inversion helpers."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

COMPONENT_DIR = (
    Path(__file__).resolve().parents[1] / "custom_components" / "hotata_airer"
)
PACKAGE = "hotata_airer"


def _ensure_package() -> None:
    if PACKAGE in sys.modules:
        return
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(COMPONENT_DIR)]
    package.__package__ = PACKAGE
    sys.modules[PACKAGE] = package


def load(name: str):
    _ensure_package()
    qualname = f"{PACKAGE}.{name}"
    if qualname in sys.modules:
        return sys.modules[qualname]
    path = COMPONENT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(qualname, path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = PACKAGE
    sys.modules[qualname] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


load("const")
invert = load("invert")
discovery = load("discovery")


class InvertPositionTests(unittest.TestCase):
    def test_swaps_ends(self) -> None:
        self.assertEqual(invert.invert_position(0), 100)
        self.assertEqual(invert.invert_position(100), 0)

    def test_midpoint_stays(self) -> None:
        self.assertEqual(invert.invert_position(50), 50)

    def test_clamps_and_rounds(self) -> None:
        self.assertEqual(invert.invert_position(12.4), 88)
        self.assertEqual(invert.invert_position(-5), 100)
        self.assertEqual(invert.invert_position(140), 0)

    def test_unknown(self) -> None:
        self.assertIsNone(invert.invert_position(None))
        self.assertIsNone(invert.invert_position("bad"))


class InvertStateTests(unittest.TestCase):
    def test_opening_becomes_closing(self) -> None:
        self.assertEqual(invert.invert_motion("opening"), (False, True))

    def test_closing_becomes_opening(self) -> None:
        self.assertEqual(invert.invert_motion("closing"), (True, False))

    def test_stopped_has_no_motion(self) -> None:
        self.assertEqual(invert.invert_motion("open"), (False, False))
        self.assertEqual(invert.invert_motion("closed"), (False, False))

    def test_closed_state_from_position(self) -> None:
        self.assertTrue(invert.invert_is_closed("open", 0))
        self.assertFalse(invert.invert_is_closed("closed", 100))
        self.assertFalse(invert.invert_is_closed("opening", 40))

    def test_closed_state_without_position(self) -> None:
        # Source fully closed → inverted fully open.
        self.assertFalse(invert.invert_is_closed("closed", None))
        # Source fully open → inverted fully closed.
        self.assertTrue(invert.invert_is_closed("open", None))


class SnapshotTests(unittest.TestCase):
    def test_full_invert_of_xiaomi_cover(self) -> None:
        snap = invert.inverted_cover_snapshot(
            "opening",
            {
                "current_position": 20,
                "supported_features": 11,  # OPEN|CLOSE|STOP
                "device_class": "blind",
            },
        )
        self.assertTrue(snap["available"])
        self.assertEqual(snap["current_position"], 80)
        self.assertFalse(snap["is_opening"])
        self.assertTrue(snap["is_closing"])
        self.assertFalse(snap["is_closed"])
        self.assertEqual(snap["supported_features"], 11)

    def test_source_closed_is_inverted_open(self) -> None:
        snap = invert.inverted_cover_snapshot(
            "closed", {"current_position": 0, "supported_features": 11}
        )
        self.assertEqual(snap["current_position"], 100)
        self.assertFalse(snap["is_closed"])
        self.assertFalse(snap["is_opening"])
        self.assertFalse(snap["is_closing"])

    def test_source_open_is_inverted_closed(self) -> None:
        snap = invert.inverted_cover_snapshot(
            "open", {"current_position": 100, "supported_features": 11}
        )
        self.assertEqual(snap["current_position"], 0)
        self.assertTrue(snap["is_closed"])

    def test_default_features_when_missing(self) -> None:
        snap = invert.inverted_cover_snapshot("open", {})
        self.assertEqual(snap["supported_features"], 1 | 2 | 8)

    def test_unavailable(self) -> None:
        snap = invert.inverted_cover_snapshot("unavailable", {})
        self.assertFalse(snap["available"])
        self.assertIsNone(snap["is_closed"])

    def test_button_mapping(self) -> None:
        self.assertEqual(invert.inverted_service_for_open(), "close_cover")
        self.assertEqual(invert.inverted_service_for_close(), "open_cover")


class DiscoveryTests(unittest.TestCase):
    def test_matches_official_model(self) -> None:
        self.assertTrue(
            discovery.is_d10zm_device(model="hotata.airer.d10zm", name="客厅晾衣架")
        )

    def test_matches_display_name(self) -> None:
        self.assertTrue(
            discovery.is_d10zm_device(model=None, name="好太太晾衣架 D10-ZM")
        )

    def test_ignores_other_airers(self) -> None:
        self.assertFalse(
            discovery.is_d10zm_device(model="hotata.airer.d3115", name="好太太")
        )

    def test_iter_xiaomi_covers(self) -> None:
        class Entry:
            def __init__(self, domain, platform, disabled=False):
                self.domain = domain
                self.platform = platform
                self.disabled = disabled

        entries = [
            Entry("cover", "xiaomi_home"),
            Entry("light", "xiaomi_home"),
            Entry("cover", "xiaomi_miot"),
            Entry("cover", "xiaomi_home", disabled=True),
        ]
        found = discovery.iter_xiaomi_covers(entries)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].platform, "xiaomi_home")


if __name__ == "__main__":
    unittest.main()
