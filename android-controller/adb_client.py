"""
ADB Client module for Android Controller.

Provides an isolated, robust subprocess-based wrapper around the Android Debug Bridge (ADB).
"""

import os
import re
import subprocess
from typing import Dict, List, Optional, Union


class ADBError(Exception):
    """Base exception for ADB operations."""
    pass


class ADBTimeoutError(ADBError):
    """Raised when an ADB command times out."""
    pass


class DeviceNotFoundError(ADBError):
    """Raised when the specified device is not found or not connected."""
    pass


class ADBClient:
    """Wrapper around ADB subprocess execution."""

    def __init__(
        self,
        adb_path: str = "adb",
        device_id: Optional[str] = None,
        default_timeout: float = 15.0,
    ) -> None:
        """
        Initialize ADBClient.

        :param adb_path: Path or command name for ADB executable.
        :param device_id: Optional serial number/ID of targeted device.
        :param default_timeout: Timeout in seconds for ADB commands.
        """
        self.adb_path = adb_path
        self.device_id = device_id
        self.default_timeout = default_timeout

    def _build_command(self, args: List[str]) -> List[str]:
        """Construct the full command list including targeted device ID if specified."""
        cmd = [self.adb_path]
        if self.device_id:
            cmd.extend(["-s", self.device_id])
        cmd.extend(args)
        return cmd

    def run_command(
        self,
        args: List[str],
        timeout: Optional[float] = None,
        check: bool = True,
        binary_output: bool = False,
    ) -> Union[str, bytes]:
        """
        Execute an ADB command with timeout and error handling.

        :param args: List of arguments to pass to ADB (e.g. ['shell', 'input', 'tap', '10', '20']).
        :param timeout: Command timeout in seconds. Defaults to self.default_timeout.
        :param check: If True, raises ADBError on non-zero exit code.
        :param binary_output: If True, returns raw bytes stdout; otherwise decodes UTF-8 string.
        :return: stdout as string or bytes.
        """
        cmd = self._build_command(args)
        cmd_timeout = timeout if timeout is not None else self.default_timeout

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=cmd_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ADBTimeoutError(
                f"ADB command timed out after {cmd_timeout}s: {' '.join(cmd)}"
            ) from exc
        except FileNotFoundError as exc:
            raise ADBError(
                f"ADB executable not found at '{self.adb_path}'. Please ensure Android SDK platform-tools are installed and on PATH."
            ) from exc
        except Exception as exc:
            raise ADBError(f"Failed to execute ADB command: {exc}") from exc

        if check and result.returncode != 0:
            stderr_msg = result.stderr.decode("utf-8", errors="replace").strip()
            stdout_msg = result.stdout.decode("utf-8", errors="replace").strip()
            err = stderr_msg if stderr_msg else stdout_msg
            err_lower = err.lower()
            if (
                "device not found" in err_lower
                or re.search(r"device\s+['\"][^'\"]+['\"]\s+not found", err_lower)
                or "no devices/emulators found" in err_lower
                or "device offline" in err_lower
            ):
                raise DeviceNotFoundError(f"Device '{self.device_id or 'default'}' not found: {err}")
            raise ADBError(f"ADB command failed with exit code {result.returncode}: {err}")


        if binary_output:
            return result.stdout
        return result.stdout.decode("utf-8", errors="replace")

    def list_devices(self) -> List[Dict[str, str]]:
        """
        List connected devices and emulators.

        :return: List of dicts with 'device_id' and 'status' (e.g. 'device', 'offline', 'unauthorized').
        """
        raw = self.run_command(["devices"], check=True)
        devices: List[Dict[str, str]] = []

        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("*") or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                devices.append({
                    "device_id": parts[0],
                    "status": parts[1],
                })
        return devices

    def launch_app(self, package_name: str, activity_name: Optional[str] = None) -> None:
        """
        Launch an application package, optionally targeting a specific activity.

        :param package_name: Application package name (e.g. 'com.example.app').
        :param activity_name: Optional activity (e.g. '.MainActivity' or 'com.example.app.MainActivity').
        """
        if activity_name:
            if not activity_name.startswith(".") and not activity_name.startswith(package_name):
                activity_component = f"{package_name}/.{activity_name}"
            elif activity_name.startswith("."):
                activity_component = f"{package_name}/{activity_name}"
            else:
                activity_component = f"{package_name}/{activity_name}"

            output = self.run_command(["shell", "am", "start", "-n", activity_component], check=True)
            if "Error:" in output:
                raise ADBError(f"Failed to start activity {activity_component}: {output.strip()}")
        else:
            output = self.run_command([
                "shell",
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ], check=True)
            if "No activities found" in output:
                raise ADBError(f"Failed to launch app {package_name}: No launcher activities found.")

    def screenshot(self, local_path: str) -> str:
        """
        Capture a screenshot and save it to the specified local path.

        :param local_path: Path where the PNG screenshot should be saved.
        :return: Absolute path of saved screenshot.
        """
        abs_path = os.path.abspath(local_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        try:
            # First attempt high-speed direct stream capture
            raw_bytes = self.run_command(
                ["exec-out", "screencap", "-p"],
                binary_output=True,
                check=True,
            )
            # Fix possible Windows CRLF line ending conversion in exec-out if any
            if isinstance(raw_bytes, bytes) and raw_bytes.startswith(b"\x89PNG"):
                with open(abs_path, "wb") as f:
                    f.write(raw_bytes)
                return abs_path
        except Exception:
            pass

        # Fallback to saving on device sdcard and pulling
        remote_path = "/sdcard/temp_screenshot.png"
        self.run_command(["shell", "screencap", "-p", remote_path], check=True)
        self.run_command(["pull", remote_path, abs_path], check=True)
        self.run_command(["shell", "rm", "-f", remote_path], check=False)
        return abs_path

    def dump_ui_hierarchy(self, local_path: Optional[str] = None) -> str:
        """
        Dump the current screen UI hierarchy XML via UIAutomator.

        :param local_path: Optional path to save the XML file locally.
        :return: UIAutomator XML string content.
        """
        remote_path = "/sdcard/window_dump.xml"
        # UIAutomator dump
        self.run_command(["shell", "uiautomator", "dump", remote_path], check=True)

        # Retrieve dump content
        try:
            xml_content = self.run_command(["exec-out", "cat", remote_path], check=True)
            if not isinstance(xml_content, str):
                xml_content = xml_content.decode("utf-8", errors="replace")
        except Exception:
            # Fallback pull
            temp_local = local_path or "temp_dump.xml"
            self.run_command(["pull", remote_path, temp_local], check=True)
            with open(temp_local, "r", encoding="utf-8", errors="replace") as f:
                xml_content = f.read()
            if not local_path and os.path.exists(temp_local):
                os.remove(temp_local)

        if local_path:
            abs_local = os.path.abspath(local_path)
            os.makedirs(os.path.dirname(abs_local), exist_ok=True)
            with open(abs_local, "w", encoding="utf-8") as f:
                f.write(xml_content)

        return xml_content

    def get_current_activity(self) -> str:
        """
        Get the current focused package/activity string.

        :return: Activity string in format 'package/activity' or empty string.
        """
        output = self.run_command(["shell", "dumpsys", "window", "windows"], check=False)
        if not output:
            output = self.run_command(["shell", "dumpsys", "activity", "activities"], check=False)

        # Look for mCurrentFocus or mFocusedApp or topResumedActivity
        patterns = [
            r"mCurrentFocus=Window\{[^\}]*\s+([a-zA-Z0-9_\.]+\/[a-zA-Z0-9_\.]+)",
            r"mFocusedApp=.*ActivityRecord\{[^\}]*\s+([a-zA-Z0-9_\.]+\/[a-zA-Z0-9_\.]+)",
            r"topResumedActivity=ActivityRecord\{[^\}]*\s+([a-zA-Z0-9_\.]+\/[a-zA-Z0-9_\.]+)",
            r"mSurface=Surface\(name=([a-zA-Z0-9_\.]+\/[a-zA-Z0-9_\.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1).strip()

        return ""

    def tap(self, x: int, y: int) -> None:
        """
        Tap on screen at coordinates (x, y).

        :param x: Horizontal pixel coordinate.
        :param y: Vertical pixel coordinate.
        """
        self.run_command(["shell", "input", "tap", str(int(x)), str(int(y))], check=True)

    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
    ) -> None:
        """
        Swipe or scroll from (x1, y1) to (x2, y2).

        :param x1: Start X coordinate.
        :param y1: Start Y coordinate.
        :param x2: End X coordinate.
        :param y2: End Y coordinate.
        :param duration_ms: Duration in milliseconds.
        """
        self.run_command([
            "shell",
            "input",
            "swipe",
            str(int(x1)),
            str(int(y1)),
            str(int(x2)),
            str(int(y2)),
            str(int(duration_ms)),
        ], check=True)

    def type_text(self, text: str) -> None:
        """
        Type text into currently focused input field.
        Escapes spaces and special shell characters.

        :param text: Text string to type.
        """
        if not text:
            return

        # ADB input text requires spaces to be represented as %s
        # and shell characters to be escaped.
        escaped_chars = []
        for char in text:
            if char == " ":
                escaped_chars.append("%s")
            elif char in ("&", "<", ">", ";", "|", "(", ")", "$", "`", "\\", "'", '"', "*", "?", "~"):
                escaped_chars.append(f"\\{char}")
            else:
                escaped_chars.append(char)

        escaped_str = "".join(escaped_chars)
        self.run_command(["shell", "input", "text", escaped_str], check=True)

    def press_back(self) -> None:
        """Press the Android Back button (KEYCODE_BACK = 4)."""
        self.run_command(["shell", "input", "keyevent", "4"], check=True)
