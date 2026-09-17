"""
Android Controller module.

Provides a unified facade (AndroidController) that coordinates ADBClient and UIParser
to connect to devices, launch apps, observe screen states, and execute actions.
"""

import os
import time
from typing import Any, Dict, Optional, Tuple, Union

try:
    from .adb_client import ADBClient, ADBError, DeviceNotFoundError
    from .ui_parser import UIParser
except (ImportError, ValueError):
    from adb_client import ADBClient, ADBError, DeviceNotFoundError
    from ui_parser import UIParser



class AndroidController:
    """High-level facade for Android device interaction, inspection, and action execution."""

    def __init__(
        self,
        adb_client: Optional[ADBClient] = None,
        output_dir: str = "artifacts/controller",
        stabilization_time: float = 1.0,
    ) -> None:
        """
        Initialize AndroidController.

        :param adb_client: Optional preconfigured ADBClient instance.
        :param output_dir: Directory where screenshots and UI hierarchies are saved.
        :param stabilization_time: Seconds to pause after an action for UI updates.
        """
        self.adb_client = adb_client or ADBClient()
        self.output_dir = output_dir
        self.stabilization_time = stabilization_time
        self.connected_device: Optional[str] = self.adb_client.device_id
        self.current_state: Optional[Dict[str, Any]] = None
        self._screen_counter: int = 0

    def connect(self, device_id: Optional[str] = None) -> str:
        """
        Connect to an active Android device or emulator.

        :param device_id: Specific device serial. If None, auto-selects available device.
        :return: Connected device serial ID.
        """
        devices = self.adb_client.list_devices()
        active_devices = [d for d in devices if d.get("status") == "device"]

        if not active_devices:
            raise DeviceNotFoundError("No active Android devices or emulators found.")

        if device_id:
            matched = next((d for d in active_devices if d["device_id"] == device_id), None)
            if not matched:
                raise DeviceNotFoundError(
                    f"Requested device '{device_id}' is not in active device list: {active_devices}"
                )
            selected = device_id
        else:
            selected = active_devices[0]["device_id"]

        self.connected_device = selected
        self.adb_client.device_id = selected
        return selected

    def launch_app(
        self,
        package_name: str,
        activity_name: Optional[str] = None,
        wait_time: float = 2.0,
    ) -> Dict[str, Any]:
        """
        Launch an application and return the resulting initial screen state.

        :param package_name: Application package name.
        :param activity_name: Optional activity name to target directly.
        :param wait_time: Seconds to wait after launch for app to render.
        :return: Current screen state dictionary.
        """
        self.adb_client.launch_app(package_name, activity_name)
        if wait_time > 0:
            time.sleep(wait_time)
        return self.get_current_state()

    def get_current_state(
        self,
        save_screenshot: bool = True,
        screenshot_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Capture the current screen state: screenshot, activity name, and structured UI elements.

        :param save_screenshot: Whether to capture and save a PNG screenshot.
        :param screenshot_name: Optional specific filename for screenshot.
        :return: Screen state dictionary {screenshot_path, current_activity, elements}.
        """
        self._screen_counter += 1

        screenshot_path = ""
        if save_screenshot:
            name = screenshot_name or f"screen_{self._screen_counter:03d}.png"
            target_screenshot_path = os.path.join(self.output_dir, "screenshots", name)
            screenshot_path = self.adb_client.screenshot(target_screenshot_path)

        hierarchy_name = f"hierarchy_{self._screen_counter:03d}.xml"
        target_hierarchy_path = os.path.join(self.output_dir, "hierarchies", hierarchy_name)
        xml_content = self.adb_client.dump_ui_hierarchy(target_hierarchy_path)

        elements = UIParser.parse(xml_content)
        current_activity = self.adb_client.get_current_activity()

        state = {
            "screenshot_path": screenshot_path,
            "current_activity": current_activity,
            "elements": elements,
        }
        self.current_state = state
        return state

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a structured action and return the resulting screen state.

        Supported actions:
        - tap: {"action": "tap", "target": {"element_id": "..."}} or {"action": "tap", "target": {"coordinates": [x, y]}}
        - back: {"action": "back"}
        - scroll: {"action": "scroll", "direction": "down"|"up"|"left"|"right", ...}
        - type: {"action": "type", "text": "...", "target": {"element_id": "..."} (optional)}
        - wait: {"action": "wait", "duration": float}

        :param action: Action dictionary.
        :return: Resulting screen state dictionary.
        """
        if not isinstance(action, dict):
            raise ValueError("Action must be a dictionary.")

        action_name = action.get("action", "").lower().strip()
        if not action_name:
            raise ValueError("Action dictionary must specify 'action'.")

        if action_name == "tap":
            self._execute_tap(action)
        elif action_name == "back":
            self._execute_back(action)
        elif action_name == "scroll":
            self._execute_scroll(action)
        elif action_name == "type":
            self._execute_type(action)
        elif action_name == "wait":
            self._execute_wait(action)
        else:
            raise ValueError(f"Unsupported action: '{action_name}'. Supported: tap, back, scroll, type, wait.")

        # Brief wait for UI to stabilize
        if self.stabilization_time > 0:
            time.sleep(self.stabilization_time)

        return self.get_current_state()

    def _resolve_target_coordinates(self, target: Any) -> Tuple[int, int]:
        """Resolve target coordinates from an element_id or coordinate pair."""
        if not isinstance(target, dict):
            raise ValueError(f"Action target must be a dictionary, got {type(target)}")

        if "coordinates" in target:
            coords = target["coordinates"]
            if len(coords) == 2:
                return (int(coords[0]), int(coords[1]))
            raise ValueError(f"Coordinates must be a list of [x, y], got {coords}")

        if "center" in target:
            coords = target["center"]
            if len(coords) == 2:
                return (int(coords[0]), int(coords[1]))
            raise ValueError(f"Center must be a list of [x, y], got {coords}")

        element_id = target.get("element_id")
        if not element_id:
            raise ValueError("Action target must contain either 'element_id' or 'coordinates'.")

        if not self.current_state or "elements" not in self.current_state:
            # If no cached state, fetch current state first
            self.get_current_state()

        elements = self.current_state.get("elements", [])
        element = UIParser.find_element_by_id(elements, element_id)

        if not element:
            raise ValueError(f"Target element with element_id '{element_id}' not found on current screen.")

        center = element.get("center")
        if not center or len(center) != 2:
            raise ValueError(f"Target element '{element_id}' does not have valid center coordinates.")

        return (int(center[0]), int(center[1]))

    def _execute_tap(self, action: Dict[str, Any]) -> None:
        target = action.get("target")
        if not target and "coordinates" in action:
            target = {"coordinates": action["coordinates"]}

        if not target:
            raise ValueError("Tap action requires 'target' specifying element_id or coordinates.")

        x, y = self._resolve_target_coordinates(target)
        self.adb_client.tap(x, y)

    def _execute_back(self, action: Dict[str, Any]) -> None:
        self.adb_client.press_back()

    def _execute_scroll(self, action: Dict[str, Any]) -> None:
        direction = action.get("direction", "down").lower()
        duration_ms = int(action.get("duration_ms", 300))

        # Check if coordinates explicitly provided
        if "start_coordinates" in action and "end_coordinates" in action:
            x1, y1 = action["start_coordinates"]
            x2, y2 = action["end_coordinates"]
            self.adb_client.swipe(x1, y1, x2, y2, duration_ms)
            return

        # Check if scrolling a specific target element
        target = action.get("target")
        if target:
            element_id = target.get("element_id")
            if element_id:
                if not self.current_state or "elements" not in self.current_state:
                    self.get_current_state()
                elem = UIParser.find_element_by_id(self.current_state.get("elements", []), element_id)
                if elem and "bounds" in elem:
                    b = elem["bounds"]
                    x1, y1, x2, y2 = self._calc_scroll_coords(b[0], b[1], b[2], b[3], direction)
                    self.adb_client.swipe(x1, y1, x2, y2, duration_ms)
                    return

        # Default full-screen scroll (default 1080x1920 reference proportions if unknown)
        x1, y1, x2, y2 = self._calc_scroll_coords(0, 0, 1080, 1920, direction)
        self.adb_client.swipe(x1, y1, x2, y2, duration_ms)

    @staticmethod
    def _calc_scroll_coords(
        left: int, top: int, right: int, bottom: int, direction: str
    ) -> Tuple[int, int, int, int]:
        mid_x = (left + right) // 2
        mid_y = (top + bottom) // 2
        height = bottom - top
        width = right - left

        if direction == "down":
            # Swiping from lower to upper scrolls content down
            return (mid_x, top + int(height * 0.75), mid_x, top + int(height * 0.25))
        elif direction == "up":
            # Swiping from upper to lower scrolls content up
            return (mid_x, top + int(height * 0.25), mid_x, top + int(height * 0.75))
        elif direction == "left":
            return (left + int(width * 0.8), mid_y, left + int(width * 0.2), mid_y)
        elif direction == "right":
            return (left + int(width * 0.2), mid_y, left + int(width * 0.8), mid_y)
        else:
            raise ValueError(f"Invalid scroll direction '{direction}'. Must be down, up, left, or right.")

    def _execute_type(self, action: Dict[str, Any]) -> None:
        text = action.get("text", "")
        target = action.get("target")

        # If target element specified, tap it first to focus
        if target:
            x, y = self._resolve_target_coordinates(target)
            self.adb_client.tap(x, y)
            time.sleep(0.5)

        self.adb_client.type_text(text)

    def _execute_wait(self, action: Dict[str, Any]) -> None:
        duration = float(action.get("duration", 1.0))
        if duration > 0:
            time.sleep(duration)
