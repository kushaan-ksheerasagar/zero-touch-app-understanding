"""
Main ExplorationAgent class.

Coordinates screen ingestion, memory tracking, and action selection.
"""

import json
from typing import Any, Dict, Optional, Union
from .memory import ExplorationMemory
from .reasoning import BaseReasoner, ReasoningContext, build_reasoning_context
from .safety import SafetyValidator, validate_action
from .selector import ActionSelector
from .semantic import ScreenUnderstanding, analyze_screen
from .types import AgentAction


class ExplorationAgent:
    """Autonomous agent brain for exploring app screens."""

    def __init__(
        self,
        memory: Optional[ExplorationMemory] = None,
        selector: Optional[ActionSelector] = None,
        reasoner: Optional[BaseReasoner] = None,
        safety_validator: Optional[SafetyValidator] = None,
    ) -> None:
        self.memory = memory if memory is not None else ExplorationMemory()
        self.selector = selector if selector is not None else ActionSelector()
        self.reasoner = reasoner
        self.safety_validator = safety_validator if safety_validator is not None else SafetyValidator()
        self.last_understanding: Optional[ScreenUnderstanding] = None
        self.last_context: Optional[ReasoningContext] = None
        self.step_count: int = 0

    def step(self, screen_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a single decision step:
        1. Accepts structured representation of the current screen.
        2. Records screen visit.
        3. Derives semantic understanding.
        4. Selects an action (via reasoner + safety validation if provided, else selector).
        5. Records the decision in memory.
        6. Returns the structured action dict.

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
        self.step_count += 1

        # 3. Select next action
        if self.reasoner is not None:
            # Reasoning pipeline: screen_dict -> semantic understanding -> ReasoningContext -> reasoner.decide() -> safety validation -> AgentAction
            self.last_context = build_reasoning_context(
                screen_data=screen_dict,
                understanding=self.last_understanding,
                memory=self.memory,
                screen_id=screen_id,
                exploration_step=self.step_count,
            )
            raw_action: AgentAction = self.reasoner.decide(self.last_context)

            # Safety validation
            val_result = self.safety_validator.validate_action(raw_action, self.last_context)
            if val_result.allowed:
                action_decision = raw_action
            else:
                action_decision = AgentAction(
                    action="back",
                    reason=f"Blocked by safety policy: {val_result.reason}",
                )

            # Loop prevention: detect if chosen element was already attempted on this screen
            target_el_id = None
            if action_decision.target is not None:
                if hasattr(action_decision.target, "element_id"):
                    target_el_id = action_decision.target.element_id
                elif isinstance(action_decision.target, dict):
                    target_el_id = action_decision.target.get("element_id")

            if target_el_id and self.memory.is_element_attempted(screen_id, str(target_el_id)):
                action_decision = AgentAction(
                    action="back",
                    reason=f"Loop prevention: element '{target_el_id}' already attempted on screen '{screen_id}'",
                )
        else:
            action_decision = self.selector.select_action(
                screen_id=screen_id,
                elements=elements,
                memory=self.memory,
            )

        # 4. Record attempted action in exploration memory
        element_id = None
        if action_decision.target is not None:
            if hasattr(action_decision.target, "element_id"):
                element_id = action_decision.target.element_id
            elif isinstance(action_decision.target, dict):
                element_id = action_decision.target.get("element_id")

        self.memory.record_attempt(
            screen_id=screen_id,
            action=action_decision.action,
            element_id=element_id,
        )

        return action_decision.to_dict()

    def get_current_understanding(self) -> Optional[ScreenUnderstanding]:
        """Returns the semantic understanding of the most recently visited screen."""
        return self.last_understanding

    def get_current_context(self) -> Optional[ReasoningContext]:
        """Returns the compact reasoning context of the most recently visited screen."""
        return self.last_context

    def get_memory(self) -> ExplorationMemory:
        """Returns the internal exploration memory."""
        return self.memory

    def reset(self) -> None:
        """Resets the agent's memory and state."""
        self.memory.clear()
        self.last_understanding = None
        self.last_context = None
        self.step_count = 0

