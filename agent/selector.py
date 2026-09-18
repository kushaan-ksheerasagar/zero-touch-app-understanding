"""
Action selection logic for the Exploration Agent.

Identifies interactive elements, checks memory, and selects the next action.
"""

from typing import Any, Dict, List, Optional
from .memory import ExplorationMemory
from .semantic import ElementRole, classify_element, extract_label
from .types import ActionTarget, AgentAction


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

    INTERACTIVE_ROLES = {
        ElementRole.NAVIGATION,
        ElementRole.BUTTON,
        ElementRole.TEXT_INPUT,
        ElementRole.LIST_ITEM,
        ElementRole.CHECKBOX,
        ElementRole.SWITCH,
        ElementRole.RADIO,
    }

    @staticmethod
    def is_system_element(element_id: str) -> bool:
        """Determines if an element belongs to non-actionable System UI overlays."""
        if not element_id:
            return False
        lower_id = element_id.lower()
        if "com.android.systemui" in lower_id:
            return True
        if "statusbarbackground" in lower_id or "navigationbarbackground" in lower_id:
            return True
        if "scrim_behind" in lower_id or "scrim_in_front" in lower_id or ":id/scrim" in lower_id:
            return True
        return False

    @classmethod
    def compute_element_priority(cls, element: Dict[str, Any]) -> int:
        """
        Computes a deterministic priority score for UI elements based on
        semantic role, meaningful labels, and application resource IDs.
        """
        score = 0
        semantic_meta = classify_element(element)
        role = semantic_meta.get("role", ElementRole.UNKNOWN)
        label = semantic_meta.get("label", "")
        el_id = str(element.get("element_id", "") or "")

        # 1. Semantic role tier scoring
        role_scores = {
            ElementRole.NAVIGATION: 50,
            ElementRole.BUTTON: 45,
            ElementRole.TEXT_INPUT: 40,
            ElementRole.LIST_ITEM: 35,
            ElementRole.CHECKBOX: 25,
            ElementRole.SWITCH: 25,
            ElementRole.RADIO: 25,
            ElementRole.IMAGE: 20,
            ElementRole.TEXT: 15,
            ElementRole.SCROLL_CONTAINER: 10,
            ElementRole.UNKNOWN: 5 if element.get("clickable") else 0,
        }
        score += role_scores.get(role, 0)

        # 2. Meaningful label signals
        if label:
            score += 15
            lower_label = label.lower()
            action_intent_cues = (
                "search",
                "next",
                "continue",
                "sign in",
                "login",
                "submit",
                "settings",
                "profile",
                "menu",
                "about",
                "open",
                "view",
                "save",
                "edit",
                "done",
                "go",
                "ok",
                "yes",
                "item",
                "product",
                "card",
                "catalog",
                "detail",
            )
            if any(cue in lower_label for cue in action_intent_cues):
                score += 15

        # 3. Real application resource ID
        if el_id and not el_id.startswith("elem_"):
            score += 10
            if ":id/" in el_id and not el_id.startswith("android:id/"):
                score += 5

        # 4. Explicit clickable flag
        if element.get("clickable"):
            score += 5

        return score

    def is_interactive(self, element: Dict[str, Any]) -> bool:
        """Determines if a UI element is interactive/clickable and actionable."""
        # 1. Ignore disabled elements
        if element.get("enabled") is False:
            return False

        # 2. Ignore zero-dimension / invisible bounds
        bounds = element.get("bounds")
        if isinstance(bounds, list) and len(bounds) == 4:
            if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                return False

        # 3. Check semantic role
        semantic_meta = classify_element(element)
        role = semantic_meta.get("role", ElementRole.UNKNOWN)
        if role in self.INTERACTIVE_ROLES:
            return True

        # 4. Check explicit clickable flag
        if "clickable" in element:
            if bool(element["clickable"]):
                return True
            return element.get("type", "").lower() in self.INTERACTIVE_TYPES

        # 5. Check element type
        el_type = str(element.get("type", "")).lower()
        if el_type in self.INTERACTIVE_TYPES:
            return True

        # 6. Check action field
        if element.get("action") in ("tap", "click", "type"):
            return True

        return False

    def get_interactive_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters a list of UI elements down to valid, non-system interactive ones."""
        interactive: List[Dict[str, Any]] = []
        for el in elements:
            if not isinstance(el, dict):
                continue
            el_id = el.get("element_id")
            if not el_id:
                continue
            if self.is_system_element(el_id):
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
        
        Filters out system overlays, prioritizes meaningful unattempted controls,
        and returns 'back' when all candidates on the screen have been explored.
        """
        interactive_elements = self.get_interactive_elements(elements)

        # Filter out already attempted elements
        unexplored = [
            el for el in interactive_elements
            if not memory.is_element_attempted(screen_id, el["element_id"])
        ]

        if not unexplored:
            return AgentAction(action="back")

        # Deterministic ranking: highest priority score first (stable sort preserves order for ties)
        unexplored.sort(key=self.compute_element_priority, reverse=True)

        selected_element = unexplored[0]
        element_id = selected_element["element_id"]

        # Formulate semantic explanation
        semantic_meta = classify_element(selected_element)
        role = semantic_meta.get("role", ElementRole.UNKNOWN)
        label = semantic_meta.get("label", "")
        if label:
            reason = f"semantic_role={role}; label={label}; unexplored"
        else:
            reason = f"semantic_role={role}; unexplored"

        target = ActionTarget(element_id=element_id)
        return AgentAction(action="tap", target=target, reason=reason)


