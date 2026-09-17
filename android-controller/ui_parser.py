"""
UI Parser module for Android Controller.

Parses UIAutomator XML hierarchies into structured Python dictionaries representing UI elements.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


# Regex to parse UIAutomator bounds: [x1,y1][x2,y2]
BOUNDS_PATTERN = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")

# Known container classes that are purely structural when non-interactive and empty
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


def parse_bounds(bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
    """
    Parse bounds string '[x1,y1][x2,y2]' into a tuple (x1, y1, x2, y2).
    Returns None if format is invalid.
    """
    if not bounds_str:
        return None
    match = BOUNDS_PATTERN.match(bounds_str.strip())
    if not match:
        return None
    x1, y1, x2, y2 = map(int, match.groups())
    return (x1, y1, x2, y2)


def compute_center(bounds: Tuple[int, int, int, int]) -> Tuple[int, int]:
    """Compute integer center coordinates (center_x, center_y) from bounds."""
    x1, y1, x2, y2 = bounds
    return ((x1 + x2) // 2, (y1 + y2) // 2)


class UIParser:
    """Parses Android UIAutomator XML trees into structured element definitions."""

    @staticmethod
    def parse(
        xml_content: str,
        filter_containers: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Parse UIAutomator XML string into a list of structured UI elements.

        :param xml_content: Raw XML string from UIAutomator dump.
        :param filter_containers: If True, filters out non-interactive layout containers.
        :return: List of element dictionaries.
        """
        if not xml_content or not xml_content.strip():
            return []

        try:
            root = ET.fromstring(xml_content.strip())
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse UIAutomator XML: {exc}") from exc

        elements: List[Dict[str, Any]] = []
        counter = {"index": 0}

        def traverse(node: ET.Element) -> None:
            if node.tag == "node":
                element = UIParser._parse_node(node, counter["index"])
                counter["index"] += 1

                is_container = len(list(node)) > 0
                if not filter_containers or UIParser._should_keep_element(element, is_container):
                    elements.append(element)

            for child in node:
                traverse(child)

        traverse(root)
        return elements

    @staticmethod
    def _parse_node(node: ET.Element, index: int) -> Dict[str, Any]:
        """Convert an XML node into a standardized element dictionary."""
        attrib = node.attrib

        resource_id = attrib.get("resource-id", "").strip()
        class_type = attrib.get("class", "").strip() or "android.view.View"
        text = attrib.get("text", "").strip()
        content_desc = attrib.get("content-desc", "").strip()
        bounds_raw = attrib.get("bounds", "")

        bounds_tuple = parse_bounds(bounds_raw) or (0, 0, 0, 0)
        bounds_list = [bounds_tuple[0], bounds_tuple[1], bounds_tuple[2], bounds_tuple[3]]
        center = list(compute_center(bounds_tuple))

        clickable = attrib.get("clickable", "false").lower() == "true"
        scrollable = attrib.get("scrollable", "false").lower() == "true"
        focusable = attrib.get("focusable", "false").lower() == "true"
        enabled = attrib.get("enabled", "true").lower() == "true"

        # Deterministic fallback element ID if resource-id is missing
        if resource_id:
            element_id = resource_id
        else:
            short_class = class_type.split(".")[-1]
            element_id = f"elem_{index:03d}_{short_class}_{bounds_list[0]}_{bounds_list[1]}"

        return {
            "element_id": element_id,
            "type": class_type,
            "text": text,
            "content_description": content_desc,
            "bounds": bounds_list,
            "center": center,
            "clickable": clickable,
            "scrollable": scrollable,
            "focusable": focusable,
            "enabled": enabled,
        }

    @staticmethod
    def _should_keep_element(element: Dict[str, Any], is_container: bool) -> bool:
        """
        Determine if an element should be kept in the output.
        Filters out pure layout wrappers while preserving all interactive and content nodes.
        """
        # Always keep interactive elements
        if element["clickable"] or element["scrollable"] or element["focusable"]:
            return True

        # Always keep elements with textual or descriptive content
        if element["text"] or element["content_description"]:
            return True

        bounds = element["bounds"]
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]

        # Ignore 0-dimension non-content elements
        if width <= 0 or height <= 0:
            return False

        # If it has children and is a known container or layout class, filter it out
        if is_container:
            elem_type = element["type"]
            if elem_type in LAYOUT_CONTAINER_CLASSES or elem_type.endswith("Layout") or elem_type.endswith("ViewGroup"):
                return False

        return True

    @staticmethod
    def find_element_by_id(elements: List[Dict[str, Any]], element_id: str) -> Optional[Dict[str, Any]]:
        """Find an element by its element_id."""
        for elem in elements:
            if elem["element_id"] == element_id:
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
        target = text.lower()
        for elem in elements:
            elem_text = elem.get("text", "").lower()
            if exact and elem_text == target:
                matches.append(elem)
            elif not exact and target in elem_text:
                matches.append(elem)
        return matches
