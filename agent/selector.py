"""
Action selection logic for the Exploration Agent.

Identifies interactive elements, checks memory, and selects the next action.
"""

from typing import Any, Dict, List, Optional
from .types import AgentAction, ActionTarget
from .memory import ExplorationMemory


class ActionSelector:
    """Evaluates screen elements and determines the next exploration action."""

    INTERACTIVE_TYPES = {
        "button",
        "clickable",
        "imagebutton",
        "image_button",
        "input",
        "edit_text",
        "edittext",
        "checkbox",
        "radiobutton",
        "radio_button",
        "switch",
        "tab",
    }

    def is_interactive(self, element: Dict[str, Any]) -> bool:
        """Determines if a UI element is interactive/clickable."""
        # 1. Check explicit clickable flag if present
        if "clickable" in element:
            if bool(element["clickable"]):
                return True
            # If explicitly clickable=False, but it has a tap action or is a button:
            return element.get("type", "").lower() in self.INTERACTIVE_TYPES

        # 2. Check element type
        el_type = str(element.get("type", "")).lower()
        if el_type in self.INTERACTIVE_TYPES:
            return True

        # 3. Check action field if specified in element
        if element.get("action") in ("tap", "click"):
            return True

        return False

    def get_interactive_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters a list of UI elements down to interactive ones that have an element_id."""
        interactive: List[Dict[str, Any]] = []
        for el in elements:
            if not isinstance(el, dict):
                continue
            if not el.get("element_id"):
                continue
            if self.is_interactive(el):
                interactive.append(el)
        return interactive

    def select_action(
        self,
        screen_id: str,
        elements: List[Dict[str, Any]],
        memory: ExplorationMemory,
    ) -> AgentAction:
        """
        Determines the next action for a screen.
        
        Prioritizes unattempted interactive elements (using 'tap').
        If all interactive elements on the screen have been attempted, returns 'back'.
        """
        interactive_elements = self.get_interactive_elements(elements)

        # Look for the first unexplored interactive element
        for el in interactive_elements:
            element_id = el["element_id"]
            if not memory.is_element_attempted(screen_id, element_id):
                target = ActionTarget(element_id=element_id)
                return AgentAction(action="tap", target=target)

        # If all interactive elements on this screen have been explored, navigate back
        return AgentAction(action="back")
