"""ADB Client module.

Provides a clean, isolated interface for executing Android Debug Bridge (ADB)
commands against connected Android emulators and physical devices.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class ADBError(Exception):
    """Base exception for ADB-related errors."""
    pass


class ADBTimeoutError(ADBError):
    """Raised when an ADB command times out."""
    pass


class DeviceNotFoundError(ADBError):
    """Raised when no Android device or emulator is detected."""
    pass


class CommandRunner:
    """Default command runner using Python's subprocess module."""

    def run(
        self,
        cmd: List[str],
        timeout: float = 10.0,
        binary: bool = False,
    ) -> Tuple[Union[str, bytes], str, int]:
        """Execute a command via subprocess.

        Args:
            cmd: Command arguments list.
            timeout: Command timeout in seconds.
            binary: If True, stdout is returned as bytes.

        Returns:
            Tuple of (stdout, stderr, returncode).
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                text=not binary,
            )
            return (
                result.stdout,
                result.stderr if not binary else result.stderr.decode("utf-8", errors="replace"),
                result.returncode,
            )
        except FileNotFoundError as exc:
            raise ADBError(
                f"ADB executable not found at '{cmd[0]}'. "
                "Please verify that Android SDK platform-tools are installed and added to PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ADBTimeoutError(
                f"Command {' '.join(cmd)} timed out after {timeout} seconds."
            ) from exc


class ADBClient:
    """Client for issuing commands to Android devices via ADB."""

    def __init__(
        self,
        adb_path: Optional[str] = None,
        device_id: Optional[str] = None,
        runner: Optional[CommandRunner] = None,
    ) -> None:
        """Initialize the ADBClient.

        Args:
            adb_path: Path to the adb binary. Defaults to ADB_PATH env or PATH.
            device_id: Optional default device identifier for this client.
            runner: Custom CommandRunner instance (useful for unit testing).
        """
        self.adb_path = adb_path or os.environ.get("ADB_PATH") or self._discover_adb()
        self.device_id = device_id
        self.runner = runner or CommandRunner()

    @staticmethod
    def _discover_adb() -> str:
        """Attempt to locate adb in PATH or common Android SDK locations."""
        which_adb = shutil.which("adb")
        if which_adb:
            return which_adb

        for env_var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
            sdk_root = os.environ.get(env_var)
            if sdk_root:
                candidate = os.path.join(sdk_root, "platform-tools", "adb")
                if os.path.isfile(candidate) or os.path.isfile(candidate + ".exe"):
                    return candidate

        return "adb"

    def _build_base_cmd(self, device_id: Optional[str] = None) -> List[str]:
        """Construct the base ADB command with optional device targeting."""
        cmd = [self.adb_path]
        target = device_id or self.device_id
        if target:
            cmd.extend(["-s", target])
        return cmd

    def list_devices(self) -> List[Dict[str, str]]:
        """List all connected Android devices and emulators.

        Returns:
            List of dictionaries with 'device_id', 'state', and 'status' keys.
        """
        cmd = [self.adb_path, "devices"]
        stdout, stderr, code = self.runner.run(cmd, timeout=5.0)

        if code != 0:
            raise ADBError(f"Failed to list devices: {stderr}")

        devices: List[Dict[str, str]] = []
        for line in str(stdout).strip().splitlines():
            line = line.strip()
            # Ignore header, blank lines, and daemon startup messages (e.g. * daemon started *)
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                state = parts[1]
                devices.append({
                    "device_id": device_id,
                    "state": state,
                    "status": state,
                })
        return devices

    def execute_shell(
        self,
        command: Union[str, List[str]],
        device_id: Optional[str] = None,
        timeout: float = 15.0,
    ) -> str:
        """Execute a shell command on the target Android device.

        Args:
            command: Shell command string or list of argument strings.
            device_id: Optional device identifier.
            timeout: Maximum execution time in seconds.

        Returns:
            Standard output of the command.
        """
        cmd = self._build_base_cmd(device_id)
        cmd.append("shell")
        if isinstance(command, list):
            cmd.extend(command)
        else:
            cmd.append(command)

        stdout, stderr, code = self.runner.run(cmd, timeout=timeout)
        if code != 0:
            raise ADBError(f"Shell command failed with code {code}: {stderr}")
        return str(stdout)

    def launch_app(
        self,
        package_name: str,
        activity_name: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> bool:
        """Launch an Android application given its package and optional activity.

        Args:
            package_name: Target package name (e.g. 'com.example.app').
            activity_name: Optional main activity name (e.g. '.MainActivity').
            device_id: Optional device identifier.

        Returns:
            True if launch command executed successfully.
        """
        if activity_name:
            if "/" in activity_name:
                target = activity_name
            elif activity_name.startswith("."):
                target = f"{package_name}/{activity_name}"
            elif not activity_name.startswith(package_name):
                target = f"{package_name}/.{activity_name}"
            else:
                target = f"{package_name}/{activity_name}"
            cmd = ["am", "start", "-n", target]
        else:
            # Fallback to monkey launcher if specific activity is not specified
            cmd = ["monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]

        output = self.execute_shell(cmd, device_id=device_id)
        if "Error:" in output or "does not exist" in output or "No activities found" in output:
            raise ADBError(f"Failed to launch app '{package_name}': {output.strip()}")
        return True

    def take_screenshot(
        self,
        output_path: str,
        device_id: Optional[str] = None,
    ) -> str:
        """Capture a screenshot from the Android device and save locally.

        Args:
            output_path: Destination local file path.
            device_id: Optional device identifier.

        Returns:
            Local file path to the saved screenshot.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        cmd = self._build_base_cmd(device_id)
        cmd.extend(["exec-out", "screencap", "-p"])

        try:
            stdout, stderr, code = self.runner.run(cmd, timeout=10.0, binary=True)
            if code == 0 and isinstance(stdout, bytes) and stdout.startswith(b"\x89PNG"):
                with open(output_path, "wb") as f:
                    f.write(stdout)
                return output_path
        except Exception:
            pass

        # Fallback to saving on device and pulling
        remote_path = "/sdcard/screen_temp.png"
        self.execute_shell(["screencap", "-p", remote_path], device_id=device_id)
        pull_cmd = self._build_base_cmd(device_id)
        pull_cmd.extend(["pull", remote_path, output_path])
        _, pull_err, pull_code = self.runner.run(pull_cmd, timeout=10.0)
        if pull_code != 0:
            raise ADBError(f"Failed to pull screenshot from device: {pull_err}")

        # Cleanup remote temporary file
        try:
            self.execute_shell(["rm", "-f", remote_path], device_id=device_id, timeout=3.0)
        except Exception:
            pass

        return output_path

    # Alias for screenshot method
    screenshot = take_screenshot

    def dump_ui_hierarchy(
        self,
        device_id: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> str:
        """Dump UIAutomator accessibility hierarchy and return XML string.

        Args:
            device_id: Optional device identifier.
            local_path: Optional path to save the XML file locally.

        Returns:
            Raw XML hierarchy string.
        """
        remote_xml_path = "/sdcard/window_dump.xml"
        # Run uiautomator dump
        dump_output = self.execute_shell(["uiautomator", "dump", remote_xml_path], device_id=device_id, timeout=10.0)

        # Read the dumped XML content via cat
        xml_content = self.execute_shell(["cat", remote_xml_path], device_id=device_id, timeout=10.0)

        if not xml_content or "<hierarchy" not in xml_content:
            # Retry once in case dump completed with slight lag
            time.sleep(0.3)
            xml_content = self.execute_shell(["cat", remote_xml_path], device_id=device_id, timeout=10.0)

        if not xml_content or "<hierarchy" not in xml_content:
            raise ADBError(f"Failed to obtain valid UIAutomator XML dump: {xml_content[:200] if xml_content else dump_output}")

        if local_path:
            abs_local = os.path.abspath(local_path)
            os.makedirs(os.path.dirname(abs_local), exist_ok=True)
            with open(abs_local, "w", encoding="utf-8") as f:
                f.write(xml_content)

        return xml_content

    def tap(self, x: int, y: int, device_id: Optional[str] = None) -> bool:
        """Tap at the specified screen coordinates.

        Args:
            x: X-coordinate in pixels.
            y: Y-coordinate in pixels.
            device_id: Optional device identifier.

        Returns:
            True upon execution.
        """
        self.execute_shell(["input", "tap", str(int(x)), str(int(y))], device_id=device_id)
        return True

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
        device_id: Optional[str] = None,
    ) -> bool:
        """Perform a swipe gesture between two points.

        Args:
            x1: Starting X-coordinate.
            y1: Starting Y-coordinate.
            x2: Ending X-coordinate.
            y2: Ending Y-coordinate.
            duration_ms: Swipe duration in milliseconds.
            device_id: Optional device identifier.

        Returns:
            True upon execution.
        """
        self.execute_shell(
            ["input", "swipe", str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms))],
            device_id=device_id,
        )
        return True

    def type_text(self, text: str, device_id: Optional[str] = None) -> bool:
        """Type text into the currently focused input field.

        Args:
            text: Text to enter.
            device_id: Optional device identifier.

        Returns:
            True upon execution.
        """
        if not text:
            return True

        # In ADB shell input text, spaces must be encoded as %s
        # and shell control characters must be escaped.
        escaped_chars: List[str] = []
        for char in str(text):
            if char == " ":
                escaped_chars.append("%s")
            elif char in ('\\', '"', "'", '$', '`', '&', ';', '|', '<', '>', '(', ')', '*', '?', '~', '!', '#', '^', '[', ']'):
                escaped_chars.append(f"\\{char}")
            else:
                escaped_chars.append(char)

        escaped = "".join(escaped_chars)
        self.execute_shell(f'input text "{escaped}"', device_id=device_id)
        return True

    def press_back(self, device_id: Optional[str] = None) -> bool:
        """Press the Android system Back button (KEYCODE_BACK = 4).

        Args:
            device_id: Optional device identifier.

        Returns:
            True upon execution.
        """
        return self.press_key(4, device_id=device_id)

    def press_key(self, keycode: Union[int, str], device_id: Optional[str] = None) -> bool:
        """Press a specific keyevent keycode.

        Args:
            keycode: Keycode integer or string identifier (e.g. 4, 66, 111).
            device_id: Optional device identifier.

        Returns:
            True upon execution.
        """
        self.execute_shell(["input", "keyevent", str(keycode)], device_id=device_id)
        return True

    def hide_keyboard(self, device_id: Optional[str] = None) -> bool:
        """Dismiss soft keyboard safely without triggering app back navigation.

        Uses KEYCODE_ESCAPE (111) which dismisses the IME on Android.

        Args:
            device_id: Optional device identifier.

        Returns:
            True upon execution.
        """
        return self.press_key(111, device_id=device_id)

    def get_current_activity(self, device_id: Optional[str] = None) -> str:
        """Get the current focused package/activity name.

        Args:
            device_id: Optional device identifier.

        Returns:
            Current activity string (e.g., 'com.example.app/.MainActivity') or 'unknown'.
        """
        # Primary: dumpsys window
        try:
            output = self.execute_shell("dumpsys window", device_id=device_id, timeout=5.0)
            patterns = [
                r"mCurrentFocus=Window\{[^\}]*\s+([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)",
                r"mFocusedApp=.*ActivityRecord\{[^\}]*\s+([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)",
                r"mTopFocusedDisplay.*([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)",
                r"mCurrentFocus=.*([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, output)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass

        # Fallback 1: dumpsys activity activities
        try:
            output = self.execute_shell("dumpsys activity activities", device_id=device_id, timeout=5.0)
            patterns = [
                r"topResumedActivity=ActivityRecord\{[^\}]*\s+([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)",
                r"mResumedActivity:[^/]*([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)",
            ]
            for pattern in patterns:
                match = re.search(pattern, output)
                if match:
                    return match.group(1).strip()
        except Exception:
            pass

        # Fallback 2: dumpsys activity top
        try:
            output = self.execute_shell("dumpsys activity top", device_id=device_id, timeout=5.0)
            match = re.search(r"ACTIVITY\s+([a-zA-Z0-9._]+/[a-zA-Z0-9._]+)", output)
            if match:
                return match.group(1).strip()
        except Exception:
            pass

        return "unknown"

    def get_current_package(self, device_id: Optional[str] = None) -> str:
        """Get the current focused application package name.

        Args:
            device_id: Optional device identifier.

        Returns:
            Package name string or 'unknown'.
        """
        activity = self.get_current_activity(device_id=device_id)
        if activity and activity != "unknown" and "/" in activity:
            return activity.split("/")[0].strip()
        return "unknown"
