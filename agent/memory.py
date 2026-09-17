"""
Exploration Memory component.

Tracks visited screens, attempted actions on elements, and exploration history.
"""

from typing import Optional, Set, Dict, List
from .types import ActionType


class ExplorationMemory:
    def __init__(self) -> None:
        # Maps screen_id -> set of element_ids attempted on that screen
        self._attempted_elements: Dict[str, Set[str]] = {}
        # List of visited screens in order
        self._visited_screens: List[str] = []
        # Full history of attempts: list of (screen_id, action, element_id)
        self._history: List[Dict[str, Optional[str]]] = []

    def record_screen_visit(self, screen_id: str) -> None:
        """Records visiting a screen."""
        if screen_id not in self._attempted_elements:
            self._attempted_elements[screen_id] = set()
        self._visited_screens.append(screen_id)

    def record_attempt(self, screen_id: str, action: ActionType, element_id: Optional[str] = None) -> None:
        """Records an action attempted on a screen and optional element."""
        if screen_id not in self._attempted_elements:
            self._attempted_elements[screen_id] = set()
        
        if element_id:
            self._attempted_elements[screen_id].add(element_id)

        self._history.append({
            "screen_id": screen_id,
            "action": action,
            "element_id": element_id
        })

    def is_element_attempted(self, screen_id: str, element_id: str) -> bool:
        """Checks whether an element on a specific screen has already been attempted."""
        return element_id in self._attempted_elements.get(screen_id, set())

    def get_attempted_elements(self, screen_id: str) -> Set[str]:
        """Returns the set of element_ids already attempted on a screen."""
        return set(self._attempted_elements.get(screen_id, set()))

    def get_visited_screens(self) -> List[str]:
        """Returns ordered history of visited screens."""
        return list(self._visited_screens)

    def get_history(self) -> List[Dict[str, Optional[str]]]:
        """Returns chronological list of all attempted actions."""
        return list(self._history)

    def clear(self) -> None:
        """Resets all exploration memory."""
        self._attempted_elements.clear()
        self._visited_screens.clear()
        self._history.clear()
