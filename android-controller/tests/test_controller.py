"""Unit tests for AndroidController."""

import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple, Union

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adb_client import ADBClient, CommandRunner, DeviceNotFoundError
from controller import AndroidController


class MockRunner(CommandRunner):
    """Mock CommandRunner configured to return realistic Android responses."""

    def __init__(self, sample_xml: str) -> None:
        self.sample_xml = sample_xml
        self.executed_commands: List[List[str]] = []
        self.mock_devices_output = "List of devices attached\nemulator-5554\tdevice\n"

    def run(
        self,
        cmd: List[str],
        timeout: float = 10.0,
        binary: bool = False,
    ) -> Tuple[Union[str, bytes], str, int]:
        self.executed_commands.append(cmd)

        # Handle 'adb devices'
        if cmd[-1] == "devices":
            return self.mock_devices_output, "", 0

        # Handle 'exec-out screencap -p'
        if any("screencap" in arg for arg in cmd) and binary:
            return b"\x89PNG\r\n\x1a\nsimulated_screenshot", "", 0

        # Handle 'cat /sdcard/window_dump.xml'
        if any("cat" in arg for arg in cmd) and any("window_dump.xml" in arg for arg in cmd):
            return self.sample_xml, "", 0

        # Handle 'dumpsys window'
        if any("window" in arg for arg in cmd):
            return "  mCurrentFocus=Window{123 u0 com.example.zeroapp/com.example.zeroapp.LoginActivity}\n", "", 0

        # Handle 'dumpsys activity activities'
        if any("activities" in arg for arg in cmd):
            return "mResumedActivity: ActivityRecord{456 u0 com.example.zeroapp/com.example.zeroapp.LoginActivity t10}\n", "", 0

        # Default success response for input / am / monkey / uiautomator commands
        return "", "", 0


class TestAndroidController(unittest.TestCase):

    def setUp(self) -> None:
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        sample_xml_path = os.path.join(fixtures_dir, "sample_dump.xml")
        with open(sample_xml_path, "r", encoding="utf-8") as f:
            self.sample_xml = f.read()

        self.runner = MockRunner(self.sample_xml)
        self.adb = ADBClient(runner=self.runner)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.controller = AndroidController(
            adb_client=self.adb,
            screenshot_dir=self.tmp_dir.name,
            stabilization_delay=0.01,  # Short delay for fast tests
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_connect_auto_select(self) -> None:
        device_id = self.controller.connect()
        self.assertEqual(device_id, "emulator-5554")
        self.assertEqual(self.controller.device_id, "emulator-5554")

    def test_connect_prefers_emulator_5554(self) -> None:
        self.runner.mock_devices_output = (
            "List of devices attached\n"
            "device-physical-123\tdevice\n"
            "emulator-5554\tdevice\n"
        )
        device_id = self.controller.connect()
        self.assertEqual(device_id, "emulator-5554")

    def test_connect_from_environment_variable(self) -> None:
        self.runner.mock_devices_output = (
            "List of devices attached\n"
            "device-custom-999\tdevice\n"
            "emulator-5554\tdevice\n"
        )
        os.environ["ANDROID_DEVICE_ID"] = "device-custom-999"
        try:
            ctrl = AndroidController(adb_client=self.adb, stabilization_delay=0.01)
            device_id = ctrl.connect()
            self.assertEqual(device_id, "device-custom-999")
        finally:
            os.environ.pop("ANDROID_DEVICE_ID", None)

    def test_connect_specific_device(self) -> None:
        device_id = self.controller.connect(device_id="emulator-5554")
        self.assertEqual(device_id, "emulator-5554")

    def test_connect_device_not_found(self) -> None:
        with self.assertRaises(DeviceNotFoundError):
            self.controller.connect(device_id="nonexistent-device")

    def test_connect_no_devices_at_all(self) -> None:
        self.runner.mock_devices_output = "List of devices attached\n"
        with self.assertRaises(DeviceNotFoundError):
            self.controller.connect()

    def test_adb_client_alias(self) -> None:
        # Verify both self.adb and self.adb_client are accessible and identical
        self.assertIs(self.controller.adb, self.controller.adb_client)

    def test_launch_app(self) -> None:
        state = self.controller.launch_app("com.example.zeroapp", ".LoginActivity")
        self.assertIn("screenshot_path", state)
        self.assertTrue(os.path.exists(state["screenshot_path"]))
        self.assertEqual(state["current_activity"], "com.example.zeroapp/com.example.zeroapp.LoginActivity")
        self.assertEqual(state["current_package"], "com.example.zeroapp")
        self.assertIsInstance(state["elements"], list)
        self.assertTrue(len(state["elements"]) > 0)

    def test_get_current_state(self) -> None:
        state = self.controller.get_current_state()
        self.assertIn("screenshot_path", state)
        self.assertIn("current_activity", state)
        self.assertIn("current_package", state)
        self.assertEqual(state["current_package"], "com.example.zeroapp")
        self.assertIn("elements", state)

        # Verify elements match schema
        elem = state["elements"][0]
        self.assertIn("element_id", elem)
        self.assertIn("resource_id", elem)
        self.assertIn("class_name", elem)
        self.assertIn("type", elem)
        self.assertIn("text", elem)
        self.assertIn("content_description", elem)
        self.assertIn("clickable", elem)
        self.assertIn("scrollable", elem)
        self.assertIn("enabled", elem)
        self.assertIn("bounds", elem)
        self.assertIn("center", elem)

    def test_execute_tap_by_coordinates_xy(self) -> None:
        action = {"action": "tap", "x": 540, "y": 960}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        tap_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "tap", "540", "960"]
        self.assertIn(tap_cmd, self.runner.executed_commands)

    def test_execute_tap_by_coordinates_list(self) -> None:
        action = {"action": "tap", "target": {"coordinates": [540, 960]}}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        tap_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "tap", "540", "960"]
        self.assertIn(tap_cmd, self.runner.executed_commands)

    def test_execute_tap_by_element_id(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "tap",
            "target": {
                "element_id": "com.example.zeroapp:id/login_button"
            }
        }
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        tap_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "tap", "540", "975"]
        self.assertIn(tap_cmd, self.runner.executed_commands)

    def test_execute_tap_by_resource_id_fallback(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "tap",
            "target": {
                "resource_id": "com.example.zeroapp:id/login_button"
            }
        }
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        tap_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "tap", "540", "975"]
        self.assertIn(tap_cmd, self.runner.executed_commands)

    def test_execute_tap_by_text_label(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "tap",
            "target": {
                "element_id": "Sign In"
            }
        }
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        tap_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "tap", "540", "975"]
        self.assertIn(tap_cmd, self.runner.executed_commands)

    def test_execute_tap_missing_element(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "tap",
            "target": {
                "element_id": "nonexistent_button"
            }
        }
        with self.assertRaises(ValueError):
            self.controller.execute_action(action)

    def test_execute_scroll_in_scrollable_container(self) -> None:
        # Prime controller with screen elements (contains scroll_container [0, 1300][1080, 2200])
        self.controller.get_current_state()
        action = {"action": "scroll", "direction": "down"}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)

        # Container is [0, 1300][1080, 2200], mid_x=540, height=900
        # Scrolling down swipes from bottom (1300 + 675 = 1975) to top (1300 + 225 = 1525)
        swipe_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "swipe", "540", "1975", "540", "1525", "300"]
        self.assertIn(swipe_cmd, self.runner.executed_commands)

    def test_execute_scroll_target_element(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "scroll",
            "direction": "up",
            "target": {"element_id": "com.example.zeroapp:id/scroll_container"},
        }
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        # Scrolling up in [0, 1300][1080, 2200] swipes from top (1525) to bottom (1975)
        swipe_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "swipe", "540", "1525", "540", "1975", "300"]
        self.assertIn(swipe_cmd, self.runner.executed_commands)

    def test_execute_scroll_custom_coords(self) -> None:
        action = {"action": "scroll", "x1": 100, "y1": 500, "x2": 100, "y2": 200, "duration_ms": 500}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        swipe_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "swipe", "100", "500", "100", "200", "500"]
        self.assertIn(swipe_cmd, self.runner.executed_commands)

    def test_execute_swipe_action(self) -> None:
        action = {"action": "swipe", "x1": 200, "y1": 800, "x2": 200, "y2": 300, "duration_ms": 400}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        swipe_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "swipe", "200", "800", "200", "300", "400"]
        self.assertIn(swipe_cmd, self.runner.executed_commands)

    def test_execute_type_with_focus_tap(self) -> None:
        self.controller.get_current_state()
        action = {
            "action": "type",
            "target": {"element_id": "com.example.zeroapp:id/username_input"},
            "text": "testuser",
        }
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        # username_input is [100,450][980,600], center is (540, 525)
        tap_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "tap", "540", "525"]
        type_cmd = ["adb", "-s", "emulator-5554", "shell", 'input text "testuser"']
        self.assertIn(tap_cmd, self.runner.executed_commands)
        self.assertIn(type_cmd, self.runner.executed_commands)

    def test_execute_type_with_hide_keyboard(self) -> None:
        action = {"action": "type", "text": "my_query", "hide_keyboard": True}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        hide_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "keyevent", "111"]
        self.assertIn(hide_cmd, self.runner.executed_commands)

    def test_execute_type_with_press_enter(self) -> None:
        action = {"action": "type", "text": "search", "press_enter": True}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        enter_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "keyevent", "66"]
        self.assertIn(enter_cmd, self.runner.executed_commands)

    def test_execute_back(self) -> None:
        action = {"action": "back"}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)
        back_cmd = ["adb", "-s", "emulator-5554", "shell", "input", "keyevent", "4"]
        self.assertIn(back_cmd, self.runner.executed_commands)

    def test_execute_wait_seconds(self) -> None:
        action = {"action": "wait", "duration": 0.01}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)

    def test_execute_wait_duration_ms(self) -> None:
        action = {"action": "wait", "duration_ms": 10}
        state = self.controller.execute_action(action)
        self.assertIsNotNone(state)

    def test_execute_invalid_action(self) -> None:
        with self.assertRaises(ValueError):
            self.controller.execute_action({"action": "unsupported_action"})


if __name__ == "__main__":
    unittest.main()
