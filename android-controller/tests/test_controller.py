"""
Unit tests for AndroidController facade.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure android-controller directory is in sys.path
CONTROLLER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, CONTROLLER_DIR)

from adb_client import ADBClient, DeviceNotFoundError
from controller import AndroidController



class TestAndroidController(unittest.TestCase):
    """Test suite for AndroidController high-level facade."""

    def setUp(self) -> None:
        self.mock_adb = MagicMock(spec=ADBClient)
        self.mock_adb.device_id = None
        self.controller = AndroidController(
            adb_client=self.mock_adb,
            output_dir="temp_test_output",
            stabilization_time=0.0,
        )

        sample_xml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "sample_dump.xml"
        )
        with open(sample_xml_path, "r", encoding="utf-8") as f:
            self.sample_xml = f.read()

        self.mock_adb.dump_ui_hierarchy.return_value = self.sample_xml
        self.mock_adb.screenshot.return_value = "/mock/screenshots/screen_001.png"
        self.mock_adb.get_current_activity.return_value = "com.example.shop/.MainActivity"

    def test_connect_auto_select(self) -> None:
        self.mock_adb.list_devices.return_value = [
            {"device_id": "emulator-5554", "status": "device"},
            {"device_id": "phone-1234", "status": "device"},
        ]
        dev = self.controller.connect()
        self.assertEqual(dev, "emulator-5554")
        self.assertEqual(self.controller.connected_device, "emulator-5554")
        self.assertEqual(self.mock_adb.device_id, "emulator-5554")

    def test_connect_explicit_device(self) -> None:
        self.mock_adb.list_devices.return_value = [
            {"device_id": "emulator-5554", "status": "device"},
            {"device_id": "phone-1234", "status": "device"},
        ]
        dev = self.controller.connect("phone-1234")
        self.assertEqual(dev, "phone-1234")
        self.assertEqual(self.controller.connected_device, "phone-1234")

    def test_connect_no_devices(self) -> None:
        self.mock_adb.list_devices.return_value = []
        with self.assertRaises(DeviceNotFoundError):
            self.controller.connect()

    def test_connect_device_not_found(self) -> None:
        self.mock_adb.list_devices.return_value = [
            {"device_id": "emulator-5554", "status": "device"}
        ]
        with self.assertRaises(DeviceNotFoundError):
            self.controller.connect("non-existent-device")

    def test_get_current_state(self) -> None:
        state = self.controller.get_current_state()
        self.assertIn("screenshot_path", state)
        self.assertIn("current_activity", state)
        self.assertIn("elements", state)
        self.assertEqual(state["current_activity"], "com.example.shop/.MainActivity")
        self.assertGreater(len(state["elements"]), 0)
        self.assertEqual(self.controller.current_state, state)

    def test_launch_app(self) -> None:
        state = self.controller.launch_app("com.example.shop", ".MainActivity", wait_time=0.0)
        self.mock_adb.launch_app.assert_called_once_with("com.example.shop", ".MainActivity")
        self.assertIsNotNone(state)
        self.assertEqual(state["current_activity"], "com.example.shop/.MainActivity")

    def test_execute_tap_by_element_id(self) -> None:
        # Populate initial screen state
        self.controller.get_current_state()

        action = {
            "action": "tap",
            "target": {
                "element_id": "com.example.shop:id/btn_signin"
            }
        }
        # In sample_dump.xml, btn_signin bounds are [48, 640][1032, 760] -> center = [540, 700]
        res_state = self.controller.execute_action(action)
        self.mock_adb.tap.assert_called_once_with(540, 700)
        self.assertIsNotNone(res_state)

    def test_execute_tap_by_coordinates(self) -> None:
        action = {
            "action": "tap",
            "target": {
                "coordinates": [250, 450]
            }
        }
        self.controller.execute_action(action)
        self.mock_adb.tap.assert_called_once_with(250, 450)

    def test_execute_tap_unknown_element_raises_error(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "tap",
            "target": {
                "element_id": "com.example.shop:id/unknown_button"
            }
        }
        with self.assertRaises(ValueError):
            self.controller.execute_action(action)

    def test_execute_back(self) -> None:
        action = {"action": "back"}
        self.controller.execute_action(action)
        self.mock_adb.press_back.assert_called_once()

    def test_execute_scroll_down(self) -> None:
        action = {"action": "scroll", "direction": "down"}
        self.controller.execute_action(action)
        self.mock_adb.swipe.assert_called_once()
        args = self.mock_adb.swipe.call_args[0]
        # Swiping down: y1 > y2
        self.assertGreater(args[1], args[3])

    def test_execute_scroll_target_element(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "scroll",
            "direction": "down",
            "target": {
                "element_id": "com.example.shop:id/product_recycler_view"
            }
        }
        self.controller.execute_action(action)
        self.mock_adb.swipe.assert_called_once()

    def test_execute_type_with_target(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "type",
            "text": "test@example.com",
            "target": {
                "element_id": "com.example.shop:id/input_email"
            }
        }
        self.controller.execute_action(action)
        # Should tap input_email first, then type
        self.mock_adb.tap.assert_called_once()
        self.mock_adb.type_text.assert_called_once_with("test@example.com")

    def test_execute_wait(self) -> None:
        action = {"action": "wait", "duration": 0.01}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)

    def test_invalid_action_name(self) -> None:
        with self.assertRaises(ValueError):
            self.controller.execute_action({"action": "fly_to_moon"})

    def test_invalid_action_structure(self) -> None:
        with self.assertRaises(ValueError):
            self.controller.execute_action(["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()
