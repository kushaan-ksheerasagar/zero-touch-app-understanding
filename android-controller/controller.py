"""Android Controller module.

Main facade exposing high-level operations (connect, launch_app, get_current_state,
execute_action) for the Zero-Touch App Understanding system.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from adb_client import ADBClient, ADBError, ADBTimeoutError, DeviceNotFoundError
from ui_parser import UIParser, calculate_center, parse_ui_hierarchy


class AndroidController:
    """Controller interface for controlling an Android device or emulator."""

    def __init__(
        self,
        device_id: Optional[str] = None,
        adb_client: Optional[ADBClient] = None,
        screenshot_dir: str = "screenshots",
        stabilization_delay: float = 1.0,
    ) -> None:
        """Initialize the Android Controller.

        Args:
            device_id: Target Android device identifier (defaults to ANDROID_DEVICE_ID env).
            adb_client: ADBClient instance or None for default.
            screenshot_dir: Directory to save screen captures.
            stabilization_delay: Seconds to wait after an action for UI to settle.
        """
        self.device_id = device_id or os.environ.get("ANDROID_DEVICE_ID")
        self.adb = adb_client or ADBClient(device_id=self.device_id)
        # Compatibility alias for scripts referencing adb_client directly
        self.adb_client = self.adb
        self.screenshot_dir = screenshot_dir
        self.stabilization_delay = stabilization_delay
        self.target_package: Optional[str] = None
        self._screenshot_counter = 0
        self._last_elements: List[Dict[str, Any]] = []

        os.makedirs(self.screenshot_dir, exist_ok=True)

    def connect(self, device_id: Optional[str] = None) -> str:
        """Verify connection to a target Android device or auto-select one.

        Args:
            device_id: Optional specific device ID to target.

        Returns:
            Selected device identifier.

        Raises:
            DeviceNotFoundError: If no devices are connected or target device is missing.
        """
        devices = self.adb.list_devices()
        if not devices:
            raise DeviceNotFoundError(
                "No Android devices or emulators detected via ADB. "
                "Please start an Android emulator or connect a device with USB debugging enabled."
            )

        target_id = device_id or self.device_id or os.environ.get("ANDROID_DEVICE_ID")

        if target_id:
            matching = [d for d in devices if d["device_id"] == target_id]
            if not matching:
                raise DeviceNotFoundError(
                    f"Specified device '{target_id}' not found in connected devices: {devices}"
                )
            dev_state = matching[0].get("state") or matching[0].get("status")
            if dev_state != "device":
                raise ADBError(
                    f"Device '{target_id}' is not in 'device' state (current state: {dev_state})."
                )
            self.device_id = target_id
        else:
            # Auto-selection: prefer emulator-5554 if active, else first device in 'device' state
            ready_devices = [
                d for d in devices
                if (d.get("state") == "device" or d.get("status") == "device")
            ]
            if not ready_devices:
                raise DeviceNotFoundError(
                    f"Found {len(devices)} device(s), but none in 'device' state: {devices}"
                )

            # Prefer emulator-5554 if available
            preferred = [d for d in ready_devices if d["device_id"] == "emulator-5554"]
            if preferred:
                self.device_id = preferred[0]["device_id"]
            else:
                self.device_id = ready_devices[0]["device_id"]

        self.adb.device_id = self.device_id
        return self.device_id

    def launch_app(
        self,
        package_name: str,
        activity_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Launch an Android application and return the initial screen state.

        Args:
            package_name: Target package (e.g. 'com.example.app').
            activity_name: Optional main activity name.

        Returns:
            Initial screen state dictionary.
        """
        if not self.device_id:
            self.connect()

        self.target_package = package_name
        self.adb.launch_app(package_name, activity_name=activity_name, device_id=self.device_id)
        time.sleep(self.stabilization_delay)
        return self.get_current_state()

    def get_current_state(self) -> Dict[str, Any]:
        """Capture the current state of the screen.

        Returns:
            Screen state dictionary conforming to the specification:
            {
                "screenshot_path": "screenshots/screen_0001.png",
                "current_activity": "com.example.app/.MainActivity",
                "current_package": "com.example.app",
                "elements": [...]
            }
        """
        if not self.device_id:
            self.connect()

        self._screenshot_counter += 1
        screenshot_filename = f"screen_{self._screenshot_counter:04d}.png"
        screenshot_path = os.path.join(self.screenshot_dir, screenshot_filename)

        # 1. Capture screenshot
        self.adb.take_screenshot(screenshot_path, device_id=self.device_id)

        # 2. Dump and parse UI hierarchy
        xml_content = self.adb.dump_ui_hierarchy(device_id=self.device_id)
        elements = parse_ui_hierarchy(
            xml_content,
            filter_useful=True,
            filter_system_ui=True,
            target_package=self.target_package,
        )
        self._last_elements = elements

        # 3. Retrieve current activity and package
        current_activity = self.adb.get_current_activity(device_id=self.device_id)
        current_package = self.adb.get_current_package(device_id=self.device_id)
        if current_package == "unknown" and self.target_package:
            current_package = self.target_package

        return {
            "screenshot_path": screenshot_path,
            "current_activity": current_activity,
            "current_package": current_package,
            "elements": elements,
        }

    def _resolve_coordinates(self, action_dict: Dict[str, Any]) -> List[int]:
        """Resolve target screen coordinates from an action dictionary.

        Supports targets defined by:
        - {"target": {"element_id": "..."}}
        - {"target": {"resource_id": "..."}}
        - {"target": {"coordinates": [100, 200]}}
        - {"target": {"x": 100, "y": 200}}
        - {"coordinates": [100, 200]}
        - {"element_id": "..."}
        - {"x": 100, "y": 200}
        """
        target = action_dict.get("target") or {}
        if not isinstance(target, dict):
            target = {}

        # 1. Direct coordinates list/tuple [x, y]
        coords = action_dict.get("coordinates") or target.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return [int(coords[0]), int(coords[1])]

        # 2. Direct x, y integer values
        x = action_dict.get("x") if action_dict.get("x") is not None else target.get("x")
        y = action_dict.get("y") if action_dict.get("y") is not None else target.get("y")
        if x is not None and y is not None:
            return [int(x), int(y)]

        # 3. Element ID or Resource ID resolution
        element_id = (
            action_dict.get("element_id")
            or target.get("element_id")
            or target.get("resource_id")
        )

        if element_id:
            elements = self._last_elements
            # If no cached elements, fetch current hierarchy
            if not elements:
                state = self.get_current_state()
                elements = state.get("elements", [])
                self._last_elements = elements

            # Exact match by element_id
            for elem in elements:
                if elem.get("element_id") == element_id:
                    return elem["center"]

            # Exact match by resource_id
            for elem in elements:
                if elem.get("resource_id") == element_id:
                    return elem["center"]

            # Match by visible text or content description
            for elem in elements:
                if (
                    elem.get("text", "").strip() == element_id
                    or elem.get("content_description", "").strip() == element_id
                ):
                    return elem["center"]

            # Fallback: check if element_id is a partial suffix match
            for elem in elements:
                elem_eid = elem.get("element_id", "")
                elem_rid = elem.get("resource_id", "")
                if elem_eid.endswith(element_id) or elem_rid.endswith(element_id):
                    return elem["center"]

            raise ValueError(
                f"Element with ID '{element_id}' could not be found on the current screen."
            )

        raise ValueError(
            "Action requires either coordinates ([x, y]) or an 'element_id' target."
        )

    @staticmethod
    def _calc_scroll_coords(
        left: int, top: int, right: int, bottom: int, direction: str
    ) -> Tuple[int, int, int, int]:
        """Compute swipe coordinates within the bounds of a scrollable region."""
        mid_x = (left + right) // 2
        mid_y = (top + bottom) // 2
        height = max(1, bottom - top)
        width = max(1, right - left)

        if direction == "down":
            # Swiping upward scrolls content downward
            return (mid_x, top + int(height * 0.75), mid_x, top + int(height * 0.25))
        elif direction == "up":
            # Swiping downward scrolls content upward
            return (mid_x, top + int(height * 0.25), mid_x, top + int(height * 0.75))
        elif direction == "left":
            # Swiping leftward
            return (left + int(width * 0.8), mid_y, left + int(width * 0.2), mid_y)
        elif direction == "right":
            # Swiping rightward
            return (left + int(width * 0.2), mid_y, left + int(width * 0.8), mid_y)
        else:
            raise ValueError(
                f"Unsupported scroll direction '{direction}'. Use 'down', 'up', 'left', or 'right'."
            )

    def execute_action(self, action_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a requested action on the Android device and return updated state.

        Args:
            action_dict: Action specification dictionary, e.g.:
                {"action": "tap", "target": {"element_id": "com.example:id/btn"}}
                {"action": "tap", "target": {"coordinates": [540, 960]}}
                {"action": "scroll", "direction": "down"}
                {"action": "type", "text": "test", "target": {"element_id": "..."}}
                {"action": "swipe", "x1": 100, "y1": 500, "x2": 100, "y2": 200}
                {"action": "back"}
                {"action": "wait", "duration": 1.5}

        Returns:
            Updated screen state dictionary.
        """
        if not self.device_id:
            self.connect()

        if not isinstance(action_dict, dict) or "action" not in action_dict:
            raise ValueError("Invalid action: payload must be a dict containing an 'action' field.")

        action_name = str(action_dict["action"]).lower().strip()

        if action_name == "tap":
            center = self._resolve_coordinates(action_dict)
            self.adb.tap(center[0], center[1], device_id=self.device_id)

        elif action_name == "scroll":
            direction = str(action_dict.get("direction", "down")).lower()
            duration = int(action_dict.get("duration_ms", 300))

            # 1. Explicit swipe coordinates
            if all(k in action_dict for k in ("x1", "y1", "x2", "y2")):
                x1, y1, x2, y2 = (
                    int(action_dict["x1"]),
                    int(action_dict["y1"]),
                    int(action_dict["x2"]),
                    int(action_dict["y2"]),
                )
            elif "start_coordinates" in action_dict and "end_coordinates" in action_dict:
                sc = action_dict["start_coordinates"]
                ec = action_dict["end_coordinates"]
                x1, y1, x2, y2 = int(sc[0]), int(sc[1]), int(ec[0]), int(ec[1])
            else:
                # 2. Check if a scrollable target element was specified
                target = action_dict.get("target") or {}
                target_id = action_dict.get("element_id") or target.get("element_id")
                scroll_bounds: Optional[List[int]] = None

                if target_id:
                    for elem in self._last_elements:
                        if elem.get("element_id") == target_id or elem.get("resource_id") == target_id:
                            scroll_bounds = elem.get("bounds")
                            break

                # 3. If no explicit target, check if any element in screen is marked scrollable
                if not scroll_bounds:
                    for elem in self._last_elements:
                        if elem.get("scrollable"):
                            scroll_bounds = elem.get("bounds")
                            break

                # 4. Compute coordinates from bounds or default reference screen
                if scroll_bounds and len(scroll_bounds) == 4:
                    x1, y1, x2, y2 = self._calc_scroll_coords(
                        scroll_bounds[0], scroll_bounds[1], scroll_bounds[2], scroll_bounds[3], direction
                    )
                else:
                    # Default screen scroll coordinates (middle 50% vertical/horizontal)
                    if direction == "down":
                        x1, y1, x2, y2 = 540, 1600, 540, 600
                    elif direction == "up":
                        x1, y1, x2, y2 = 540, 600, 540, 1600
                    elif direction == "left":
                        x1, y1, x2, y2 = 900, 1200, 150, 1200
                    elif direction == "right":
                        x1, y1, x2, y2 = 150, 1200, 900, 1200
                    else:
                        raise ValueError(
                            f"Unsupported scroll direction '{direction}'. Use 'down', 'up', 'left', or 'right'."
                        )

            self.adb.swipe(x1, y1, x2, y2, duration_ms=duration, device_id=self.device_id)

        elif action_name == "swipe":
            x1 = int(action_dict["x1"])
            y1 = int(action_dict["y1"])
            x2 = int(action_dict["x2"])
            y2 = int(action_dict["y2"])
            duration = int(action_dict.get("duration_ms", 300))
            self.adb.swipe(x1, y1, x2, y2, duration_ms=duration, device_id=self.device_id)

        elif action_name == "type":
            text = action_dict.get("text", "")
            # If a target is provided, tap it first to focus the input field
            target = action_dict.get("target") or {}
            if (
                target
                or "element_id" in action_dict
                or "x" in action_dict
                or "coordinates" in action_dict
            ):
                try:
                    coords = self._resolve_coordinates(action_dict)
                    self.adb.tap(coords[0], coords[1], device_id=self.device_id)
                    time.sleep(0.3)
                except ValueError:
                    pass

            self.adb.type_text(str(text), device_id=self.device_id)

            if action_dict.get("hide_keyboard"):
                time.sleep(0.2)
                self.adb.hide_keyboard(device_id=self.device_id)
            if action_dict.get("press_enter"):
                time.sleep(0.2)
                self.adb.press_key(66, device_id=self.device_id)

        elif action_name == "back":
            self.adb.press_back(device_id=self.device_id)

        elif action_name == "wait":
            duration = float(
                action_dict.get("duration")
                or (action_dict.get("duration_ms", 1000) / 1000.0)
            )
            time.sleep(max(0.0, duration))

        else:
            raise ValueError(
                f"Unknown action '{action_name}'. Supported actions: tap, scroll, swipe, type, back, wait."
            )

        # UI stabilization wait before observing new state
        time.sleep(self.stabilization_delay)
        return self.get_current_state()
