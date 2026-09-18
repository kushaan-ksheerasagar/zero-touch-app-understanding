"""Unit tests for ADBClient."""

import os
import subprocess
import tempfile
import unittest
from typing import List, Tuple, Union

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adb_client import ADBClient, ADBError, ADBTimeoutError, CommandRunner


class MockCommandRunner(CommandRunner):
    """Mock runner to intercept subprocess executions during unit tests."""

    def __init__(self) -> None:
        self.executed_commands: List[List[str]] = []
        self.responses: List[Tuple[Union[str, bytes], str, int]] = []
        self.default_response: Tuple[Union[str, bytes], str, int] = ("", "", 0)

    def set_next_response(self, stdout: Union[str, bytes], stderr: str = "", code: int = 0) -> None:
        self.responses.append((stdout, stderr, code))

    def run(
        self,
        cmd: List[str],
        timeout: float = 10.0,
        binary: bool = False,
    ) -> Tuple[Union[str, bytes], str, int]:
        self.executed_commands.append(cmd)
        if self.responses:
            return self.responses.pop(0)
        return self.default_response


class TestADBClient(unittest.TestCase):

    def setUp(self) -> None:
        self.runner = MockCommandRunner()
        self.client = ADBClient(adb_path="adb", runner=self.runner)

    def test_list_devices_single_device(self) -> None:
        output = "List of devices attached\nemulator-5554\tdevice\n"
        self.runner.set_next_response(output)

        devices = self.client.list_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device_id"], "emulator-5554")
        self.assertEqual(devices[0]["state"], "device")
        self.assertEqual(devices[0]["status"], "device")
        self.assertEqual(self.runner.executed_commands[-1], ["adb", "devices"])

    def test_list_devices_multiple_and_offline(self) -> None:
        output = "List of devices attached\nemulator-5554\tdevice\nemulator-5556\toffline\n"
        self.runner.set_next_response(output)

        devices = self.client.list_devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["device_id"], "emulator-5554")
        self.assertEqual(devices[1]["state"], "offline")
        self.assertEqual(devices[1]["status"], "offline")

    def test_list_devices_ignores_daemon_startup(self) -> None:
        output = (
            "* daemon not running; starting now at tcp:5037\n"
            "* daemon started successfully\n"
            "List of devices attached\n"
            "emulator-5554\tdevice\n"
        )
        self.runner.set_next_response(output)
        devices = self.client.list_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device_id"], "emulator-5554")

    def test_list_devices_error(self) -> None:
        self.runner.set_next_response("", stderr="daemon not running", code=1)
        with self.assertRaises(ADBError):
            self.client.list_devices()

    def test_launch_app_with_activity(self) -> None:
        self.runner.set_next_response("Starting: Intent { act=android.intent.action.MAIN ... }")
        success = self.client.launch_app("com.example.app", ".MainActivity", device_id="emulator-5554")
        self.assertTrue(success)
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "am", "start", "-n", "com.example.app/.MainActivity"]
        )

    def test_launch_app_default_launcher(self) -> None:
        self.runner.set_next_response("Events injected: 1")
        success = self.client.launch_app("com.example.app", device_id="emulator-5554")
        self.assertTrue(success)
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "monkey", "-p", "com.example.app", "-c", "android.intent.category.LAUNCHER", "1"]
        )

    def test_take_screenshot_exec_out(self) -> None:
        fake_png = b"\x89PNG\r\n\x1a\nfake_image_bytes"
        self.runner.set_next_response(fake_png, code=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "screen.png")
            saved_path = self.client.take_screenshot(out_file, device_id="emulator-5554")
            self.assertEqual(saved_path, out_file)
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "rb") as f:
                self.assertEqual(f.read(), fake_png)

        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "exec-out", "screencap", "-p"]
        )

    def test_screenshot_fallback_pull(self) -> None:
        # 1. Exec-out returns corrupt/non-PNG output
        self.runner.set_next_response(b"not_png", code=1)
        # 2. screencap -p /sdcard/screen_temp.png
        self.runner.set_next_response("")
        # 3. adb pull
        self.runner.set_next_response("")
        # 4. rm -f /sdcard/screen_temp.png
        self.runner.set_next_response("")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "screen_fallback.png")
            with open(out_file, "w") as f:
                f.write("placeholder")
            saved_path = self.client.take_screenshot(out_file, device_id="emulator-5554")
            self.assertEqual(saved_path, out_file)

    def test_screenshot_alias(self) -> None:
        fake_png = b"\x89PNG\r\n\x1a\nbytes"
        self.runner.set_next_response(fake_png, code=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "alias.png")
            self.client.screenshot(out_file, device_id="emulator-5554")
            self.assertTrue(os.path.exists(out_file))

    def test_dump_ui_hierarchy(self) -> None:
        fake_xml = "<hierarchy><node text='test'/></hierarchy>"
        # Response 1: uiautomator dump output
        self.runner.set_next_response("UI hierchary dumped to: /sdcard/window_dump.xml")
        # Response 2: cat /sdcard/window_dump.xml output
        self.runner.set_next_response(fake_xml)

        xml = self.client.dump_ui_hierarchy(device_id="emulator-5554")
        self.assertEqual(xml, fake_xml)
        self.assertEqual(len(self.runner.executed_commands), 2)
        self.assertEqual(
            self.runner.executed_commands[0],
            ["adb", "-s", "emulator-5554", "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"]
        )
        self.assertEqual(
            self.runner.executed_commands[1],
            ["adb", "-s", "emulator-5554", "shell", "cat", "/sdcard/window_dump.xml"]
        )

    def test_tap(self) -> None:
        self.runner.set_next_response("")
        self.client.tap(500, 600, device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "input", "tap", "500", "600"]
        )

    def test_swipe(self) -> None:
        self.runner.set_next_response("")
        self.client.swipe(100, 200, 100, 800, duration_ms=400, device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "input", "swipe", "100", "200", "100", "800", "400"]
        )

    def test_type_text_escapes(self) -> None:
        self.runner.set_next_response("")
        self.client.type_text("Hello World & User", device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", 'input text "Hello%sWorld%s\\&%sUser"']
        )

    def test_type_text_special_characters(self) -> None:
        self.runner.set_next_response("")
        self.client.type_text('user$1;"test"', device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", 'input text "user\\$1\\;\\\"test\\\""']
        )

    def test_press_back(self) -> None:
        self.runner.set_next_response("")
        self.client.press_back(device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "input", "keyevent", "4"]
        )

    def test_press_key(self) -> None:
        self.runner.set_next_response("")
        self.client.press_key(66, device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "input", "keyevent", "66"]
        )

    def test_hide_keyboard(self) -> None:
        self.runner.set_next_response("")
        self.client.hide_keyboard(device_id="emulator-5554")
        self.assertEqual(
            self.runner.executed_commands[-1],
            ["adb", "-s", "emulator-5554", "shell", "input", "keyevent", "111"]
        )

    def test_get_current_activity(self) -> None:
        dumpsys_output = "  mCurrentFocus=Window{c7e9970 u0 com.example.zeroapp/com.example.zeroapp.MainActivity}\n"
        self.runner.set_next_response(dumpsys_output)
        activity = self.client.get_current_activity(device_id="emulator-5554")
        self.assertEqual(activity, "com.example.zeroapp/com.example.zeroapp.MainActivity")

    def test_get_current_package(self) -> None:
        dumpsys_output = "  mCurrentFocus=Window{c7e9970 u0 com.example.zeroapp/com.example.zeroapp.MainActivity}\n"
        self.runner.set_next_response(dumpsys_output)
        pkg = self.client.get_current_package(device_id="emulator-5554")
        self.assertEqual(pkg, "com.example.zeroapp")

    def test_command_runner_timeout_raises_adb_timeout_error(self) -> None:
        runner = CommandRunner()
        with self.assertRaises(ADBTimeoutError):
            # Sleep 1s with 0.05s timeout to guarantee timeout
            runner.run(["sleep", "1"], timeout=0.05)


if __name__ == "__main__":
    unittest.main()
