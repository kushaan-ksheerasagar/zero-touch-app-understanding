"""UIAutomator XML hierarchy parser.

Parses Android UIAutomator XML dumps into clean, structured Python dictionaries,
extracting element bounds, centers, labels, interaction flags, and deterministic IDs.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

# Pattern matching bounds formatted as "[x1,y1][x2,y2]"
BOUNDS_PATTERN = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")

# Known container classes that are purely structural when non-interactive and without content
LAYOUT_CONTAINER_CLASSES = {
    "android.view.View",
    "android.view.ViewGroup",
    "android.widget.FrameLayout",
    "android.widget.LinearLayout",
    "android.widget.RelativeLayout",
    "android.widget.AbsoluteLayout",
    "android.widget.TableLayout",
    "android.widget.TableRow",
    "androidx.appcompat.widget.LinearLayoutCompat",
    "androidx.constraintlayout.widget.ConstraintLayout",
    "androidx.coordinatorlayout.widget.CoordinatorLayout",
    "androidx.drawerlayout.widget.DrawerLayout",
    "androidx.recyclerview.widget.RecyclerView",
    "androidx.viewpager.widget.ViewPager",
    "androidx.viewpager2.widget.ViewPager2",
}

# Android system UI package identifiers to filter out unless explicitly targeted
SYSTEM_PACKAGES = {
    "com.android.systemui",
    "com.google.android.inputmethod.latin",
    "com.android.inputmethod.latin",
    "com.google.android.apps.nexuslauncher",
    "com.android.launcher3",
    "com.google.android.setupwizard",
}


def parse_bounds(bounds_str: str) -> Optional[List[int]]:
    """Parse a UIAutomator bounds string into [x1, y1, x2, y2].

    Args:
        bounds_str: String formatted as '[x1,y1][x2,y2]'.

    Returns:
        List of 4 integers [x1, y1, x2, y2] or None if malformed.
    """
    if not bounds_str or not isinstance(bounds_str, str):
        return None
    match = BOUNDS_PATTERN.match(bounds_str.strip())
    if not match:
        return None
    return [int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))]


def calculate_center(bounds: List[int]) -> List[int]:
    """Calculate the center coordinate [x, y] from bounds [x1, y1, x2, y2].

    Args:
        bounds: [x1, y1, x2, y2] coordinate list.

    Returns:
        [center_x, center_y] as integer pixels.
    """
    if not bounds or len(bounds) < 4:
        return [0, 0]
    x1, y1, x2, y2 = bounds
    return [(x1 + x2) // 2, (y1 + y2) // 2]


# Alias for calculate_center
compute_center = calculate_center


def is_useful_element(element: Dict[str, Any]) -> bool:
    """Determine if a UI element provides interactive or semantic value.

    Filters out empty structural layout containers that have no text and
    cannot be interacted with.

    Args:
        element: Parsed element dictionary.

    Returns:
        True if the element is interactive or has semantic content.
    """
    bounds = element.get("bounds")
    if not bounds or len(bounds) < 4:
        return False

    # Check for valid on-screen area
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    if width <= 0 or height <= 0:
        return False

    # Interactive elements are always useful
    if element.get("clickable") or element.get("scrollable") or element.get("focusable"):
        return True

    # Informational elements with text or content description
    text = (element.get("text") or "").strip()
    desc = (element.get("content_description") or "").strip()
    if text or desc:
        return True

    # Input elements (EditText) are useful even if empty and not marked clickable
    elem_type = str(element.get("type", ""))
    if elem_type.endswith("EditText") or element.get("password"):
        return True

    return False


def parse_ui_hierarchy(
    xml_content: str,
    filter_useful: bool = True,
    filter_system_ui: bool = True,
    target_package: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Parse UIAutomator XML string into a structured list of UI elements.

    Args:
        xml_content: Raw XML string from 'uiautomator dump'.
        filter_useful: If True, filters out non-interactive empty layout containers.
        filter_system_ui: If True, filters out system status bar, nav bar, and keyboard.
        target_package: Optional target app package to isolate elements for.

    Returns:
        List of element dictionaries conforming to the Phase 1 & 2 schema:
        {
            "element_id": str,
            "resource_id": str,
            "class_name": str,
            "type": str,
            "text": str,
            "content_description": str,
            "clickable": bool,
            "scrollable": bool,
            "focusable": bool,
            "enabled": bool,
            "bounds": [x1, y1, x2, y2],
            "center": [x, y],
            "package": str,
            "password": bool,
            "input_type": str
        }
    """
    if not xml_content or not xml_content.strip():
        return []

    try:
        root = ET.fromstring(xml_content.strip())
    except ET.ParseError as exc:
        raise ValueError(f"Malformed UIAutomator XML content: {exc}") from exc

    # First pass: count resource-id frequencies to detect duplicates
    resource_id_counts: Counter[str] = Counter()
    for node in root.iter():
        if node.tag == "node":
            rid = node.attrib.get("resource-id", "").strip()
            if rid:
                resource_id_counts[rid] += 1

    resource_id_seen: Counter[str] = Counter()
    elements: List[Dict[str, Any]] = []
    counter = 0

    def traverse(node: ET.Element) -> None:
        nonlocal counter
        if node.tag == "node":
            counter += 1
            attrib = node.attrib

            pkg = attrib.get("package", "").strip()

            # Filter system UI elements if requested
            if filter_system_ui:
                if target_package and pkg and pkg != target_package:
                    # If targeting a specific package, ignore other packages
                    if pkg in SYSTEM_PACKAGES:
                        return
                elif not target_package and pkg in SYSTEM_PACKAGES:
                    return

            resource_id = attrib.get("resource-id", "").strip()
            class_name = attrib.get("class", "").strip()
            text = attrib.get("text", "")
            content_desc = attrib.get("content-desc", "")
            password = attrib.get("password", "false").lower() == "true"

            # Determine input_type hint
            if password:
                input_type = "password"
            elif class_name.endswith("EditText"):
                input_type = "text"
            else:
                input_type = attrib.get("input-type", "")

            # Generate collision-free deterministic element ID
            short_class = class_name.split(".")[-1] if class_name else "Node"
            if resource_id:
                if resource_id_counts[resource_id] > 1:
                    # Disambiguate duplicate resource IDs deterministically
                    idx = resource_id_seen[resource_id]
                    resource_id_seen[resource_id] += 1
                    element_id = f"{resource_id}_{idx}"
                else:
                    element_id = resource_id
            else:
                # Deterministic fallback for unnamed nodes
                element_id = f"elem_{counter}_{short_class.lower()}"

            bounds = parse_bounds(attrib.get("bounds", ""))
            center = calculate_center(bounds) if bounds else [0, 0]

            elem_dict: Dict[str, Any] = {
                "element_id": element_id,
                "resource_id": resource_id,
                "class_name": class_name,
                "type": class_name,
                "text": text,
                "content_description": content_desc,
                "clickable": attrib.get("clickable", "false").lower() == "true",
                "scrollable": attrib.get("scrollable", "false").lower() == "true",
                "focusable": attrib.get("focusable", "false").lower() == "true",
                "enabled": attrib.get("enabled", "true").lower() == "true",
                "bounds": bounds or [0, 0, 0, 0],
                "center": center,
                "package": pkg,
                "password": password,
                "input_type": input_type,
            }

            if not filter_useful or is_useful_element(elem_dict):
                elements.append(elem_dict)

        for child in node:
            traverse(child)

    traverse(root)
    return elements


class UIParser:
    """Class interface for parsing and querying UIAutomator hierarchies."""

    @staticmethod
    def parse(
        xml_content: str,
        filter_useful: bool = True,
        filter_system_ui: bool = True,
        target_package: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Parse UIAutomator XML string into a list of structured UI elements."""
        return parse_ui_hierarchy(
            xml_content=xml_content,
            filter_useful=filter_useful,
            filter_system_ui=filter_system_ui,
            target_package=target_package,
        )

    @staticmethod
    def find_element_by_id(elements: List[Dict[str, Any]], element_id: str) -> Optional[Dict[str, Any]]:
        """Find an element by its element_id or raw resource_id."""
        for elem in elements:
            if elem.get("element_id") == element_id:
                return elem
        # Fallback to resource_id match
        for elem in elements:
            if elem.get("resource_id") == element_id:
                return elem
        return None

    @staticmethod
    def find_elements_by_text(
        elements: List[Dict[str, Any]],
        text: str,
        exact: bool = False,
    ) -> List[Dict[str, Any]]:
        """Find elements containing or matching the given text."""
        matches: List[Dict[str, Any]] = []
        target = text.lower().strip()
        for elem in elements:
            elem_text = str(elem.get("text") or "").lower().strip()
            elem_desc = str(elem.get("content_description") or "").lower().strip()
            if exact:
                if elem_text == target or elem_desc == target:
                    matches.append(elem)
            else:
                if target in elem_text or target in elem_desc:
                    matches.append(elem)
        return matches
