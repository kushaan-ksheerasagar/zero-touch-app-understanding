"""
Unit tests for ADBClient.
"""

import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

# Ensure android-controller directory is in sys.path
CONTROLLER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, CONTROLLER_DIR)

from adb_client import ADBClient, ADBError, ADBTimeoutError, DeviceNotFoundError



class TestADBClient(unittest.TestCase):
    """Test suite for ADB subprocess wrapper."""

    def setUp(self) -> None:
        self.client = ADBClient(adb_path="adb", device_id=None, default_timeout=10.0)

    def test_build_command_without_device(self) -> None:
        cmd = self.client._build_command(["devices"])
        self.assertEqual(cmd, ["adb", "devices"])

    def test_build_command_with_device(self) -> None:
        client_with_dev = ADBClient(adb_path="adb", device_id="emulator-5554")
        cmd = client_with_dev._build_command(["shell", "ls"])
        self.assertEqual(cmd, ["adb", "-s", "emulator-5554", "shell", "ls"])

    @patch("subprocess.run")
    def test_list_devices_parsing(self, mock_run: MagicMock) -> None:
        mock_output = (
            "* daemon not running; starting now at tcp:5037 *\n"
            "* daemon started successfully *\n"
            "List of devices attached\n"
            "emulator-5554\tdevice\n"
            "device-12345\toffline\n"
            "device-67890\tunauthorized\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output.encode("utf-8"), stderr=b"")

        devices = self.client.list_devices()
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0], {"device_id": "emulator-5554", "status": "device"})
        self.assertEqual(devices[1], {"device_id": "device-12345", "status": "offline"})
        self.assertEqual(devices[2], {"device_id": "device-67890", "status": "unauthorized"})

    @patch("subprocess.run")
    def test_list_devices_empty(self, mock_run: MagicMock) -> None:
        mock_output = "List of devices attached\n\n"
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output.encode("utf-8"), stderr=b"")
        devices = self.client.list_devices()
        self.assertEqual(devices, [])

    @patch("subprocess.run")
    def test_launch_app_with_activity(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"Starting: Intent ...", stderr=b"")
        self.client.launch_app("com.example.app", ".MainActivity")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("am", args)
        self.assertIn("start", args)
        self.assertIn("com.example.app/.MainActivity", args)

    @patch("subprocess.run")
    def test_launch_app_without_activity(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=b":Monkey: seed=0 count=1 ... Events injected: 1", stderr=b"")
        self.client.launch_app("com.example.app")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("monkey", args)
        self.assertIn("com.example.app", args)

    @patch("subprocess.run")
    def test_launch_app_error_handling(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=b"Error: Activity class {com.example/com.example.Bad} does not exist.",
            stderr=b"",
        )
        with self.assertRaises(ADBError):
            self.client.launch_app("com.example", ".Bad")

    @patch("subprocess.run")
    def test_get_current_activity_window_dumpsys(self, mock_run: MagicMock) -> None:
        dumpsys_output = (
            "  mCurrentFocus=Window{8d9435b u0 com.example.shop/com.example.shop.MainActivity}\n"
            "  mFocusedApp=AppWindowToken{...}\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=dumpsys_output.encode("utf-8"), stderr=b"")
        activity = self.client.get_current_activity()
        self.assertEqual(activity, "com.example.shop/com.example.shop.MainActivity")

    @patch("subprocess.run")
    def test_get_current_activity_focused_app(self, mock_run: MagicMock) -> None:
        dumpsys_output = (
            "  mCurrentFocus=null\n"
            "  mFocusedApp=ActivityRecord{a1b2c3d u0 com.example.shop/.DetailActivity t42}\n"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=dumpsys_output.encode("utf-8"), stderr=b"")
        activity = self.client.get_current_activity()
        self.assertEqual(activity, "com.example.shop/.DetailActivity")

    @patch("subprocess.run")
    def test_tap(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        self.client.tap(120, 350)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["adb", "shell", "input", "tap", "120", "350"])

    @patch("subprocess.run")
    def test_swipe(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        self.client.swipe(100, 500, 100, 200, 400)
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["adb", "shell", "input", "swipe", "100", "500", "100", "200", "400"])

    @patch("subprocess.run")
    def test_type_text_escaping(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        self.client.type_text("Hello World & Friends!")
        args = mock_run.call_args[0][0]
        self.assertEqual(args[0:4], ["adb", "shell", "input", "text"])
        # Spaces become %s and & is escaped as \&
        self.assertEqual(args[4], "Hello%sWorld%s\\&%sFriends!")

    @patch("subprocess.run")
    def test_press_back(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
        self.client.press_back()
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["adb", "shell", "input", "keyevent", "4"])

    @patch("subprocess.run")
    def test_timeout_raises_adb_timeout_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["adb", "devices"], timeout=10.0)
        with self.assertRaises(ADBTimeoutError):
            self.client.run_command(["devices"])

    @patch("subprocess.run")
    def test_file_not_found_raises_adb_error(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("adb executable not found")
        with self.assertRaises(ADBError) as ctx:
            self.client.run_command(["devices"])
        self.assertIn("executable not found", str(ctx.exception))

    @patch("subprocess.run")
    def test_device_not_found_error(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=b"",
            stderr=b"error: device 'emulator-5554' not found\n",
        )
        with self.assertRaises(DeviceNotFoundError):
            self.client.run_command(["shell", "ls"])


if __name__ == "__main__":
    unittest.main()
