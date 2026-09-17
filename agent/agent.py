"""
Main ExplorationAgent class.

Coordinates screen ingestion, memory tracking, and action selection.
"""

import json
from typing import Any, Dict, Optional, Union
from .memory import ExplorationMemory
from .selector import ActionSelector
from .semantic import ScreenUnderstanding, analyze_screen
from .types import AgentAction


class ExplorationAgent:
    """Autonomous agent brain for exploring app screens."""

    def __init__(
        self,
        memory: Optional[ExplorationMemory] = None,
        selector: Optional[ActionSelector] = None,
    ) -> None:
        self.memory = memory if memory is not None else ExplorationMemory()
        self.selector = selector if selector is not None else ActionSelector()
        self.last_understanding: Optional[ScreenUnderstanding] = None


    def step(self, screen_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a single decision step:
        1. Accepts structured representation of the current screen.
        2. Records screen visit.
        3. Selects an unexplored action.
        4. Records the decision in memory.
        5. Returns the structured action dict.

        Args:
            screen_data: Either a dictionary or a JSON string conforming to the screen schema.
                         e.g., {"screen_id": "home", "elements": [...]}

        Returns:
            Structured dictionary representing the action to take.
        """
        if isinstance(screen_data, str):
            screen_dict = json.loads(screen_data)
        elif isinstance(screen_data, dict):
            screen_dict = screen_data
        else:
            raise TypeError("screen_data must be a dict or valid JSON string")

        screen_id = screen_dict.get("screen_id", "unknown_screen")
        elements = screen_dict.get("elements", [])

        # 1. Record screen visit
        self.memory.record_screen_visit(screen_id)

        # 2. Derive semantic screen understanding
        self.last_understanding = analyze_screen(screen_dict)

        # 3. Select next action
        action_decision: AgentAction = self.selector.select_action(
            screen_id=screen_id,
            elements=elements,
            memory=self.memory,
        )

        # 4. Record attempted action in exploration memory
        element_id = None
        if action_decision.target is not None:
            element_id = action_decision.target.element_id

        self.memory.record_attempt(
            screen_id=screen_id,
            action=action_decision.action,
            element_id=element_id,
        )

        return action_decision.to_dict()

    def get_current_understanding(self) -> Optional[ScreenUnderstanding]:
        """Returns the semantic understanding of the most recently visited screen."""
        return self.last_understanding

    def get_memory(self) -> ExplorationMemory:
        """Returns the internal exploration memory."""
        return self.memory

    def reset(self) -> None:
        """Resets the agent's memory."""
        self.memory.clear()
        self.last_understanding = None

