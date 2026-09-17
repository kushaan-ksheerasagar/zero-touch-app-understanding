"""
Reasoning Architecture module for autonomous app understanding.

Transforms raw screen states and semantic understanding into a compact,
token-efficient ReasoningContext, and provides reasoner abstractions (BaseReasoner)
and deterministic implementations (RuleBasedReasoner) without external LLM dependencies.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

from .safety import SafetyValidator
from .selector import ActionSelector
from .semantic import ElementRole, ScreenUnderstanding, analyze_screen, classify_element
from .types import ActionTarget, AgentAction


@dataclass
class ReasoningContext:
    """
    Compact semantic context tailored for decision-making.
    Excludes verbose raw UI tree structures, coordinate matrices, and irrelevant metadata.
    """
    screen_id: str
    screen_type: str
    likely_purpose: str
    current_activity: str
    elements: List[Dict[str, Any]] = field(default_factory=list)
    explored_element_ids: List[str] = field(default_factory=list)
    available_interactions: List[Dict[str, Any]] = field(default_factory=list)
    recent_actions: List[Dict[str, Any]] = field(default_factory=list)
    recent_screens: List[str] = field(default_factory=list)
    exploration_step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "screen_type": self.screen_type,
            "likely_purpose": self.likely_purpose,
            "current_activity": self.current_activity,
            "elements": self.elements,
            "explored_element_ids": self.explored_element_ids,
            "available_interactions": self.available_interactions,
            "recent_actions": self.recent_actions,
            "recent_screens": self.recent_screens,
            "exploration_step": self.exploration_step,
        }


def build_reasoning_context(
    screen_data: Dict[str, Any],
    understanding: Optional[ScreenUnderstanding] = None,
    memory: Optional[Any] = None,
    screen_id: Optional[str] = None,
    exploration_step: int = 0,
) -> ReasoningContext:
    """
    Constructs a deterministic, compact ReasoningContext from raw screen data,
    semantic understanding, and exploration memory.
    """
    assigned_screen_id = str(
        screen_id or screen_data.get("screen_id", "") or "screen_unknown"
    )
    current_activity = str(screen_data.get("current_activity", "") or "")

    # Derive understanding if not provided
    if understanding is None:
        understanding = analyze_screen(screen_data)

    # Determine explored elements
    explored_set: Set[str] = set()
    recent_actions: List[Dict[str, Any]] = []
    recent_screens: List[str] = []

    if memory is not None:
        if hasattr(memory, "get_attempted_elements"):
            explored_set = set(memory.get_attempted_elements(assigned_screen_id))
        if hasattr(memory, "get_history"):
            history = memory.get_history() or []
            recent_actions = history[-5:]
        if hasattr(memory, "get_visited_screens"):
            visited = memory.get_visited_screens() or []
            recent_screens = visited[-5:]

    # Extract compact semantic elements (no raw bounds, center, or deep XML hierarchy)
    compact_elements: List[Dict[str, Any]] = []
    available_interactions: List[Dict[str, Any]] = []

    for raw_elem in understanding.elements:
        if not isinstance(raw_elem, dict):
            continue

        el_id = str(raw_elem.get("element_id", "") or "")
        role = str(raw_elem.get("role", ElementRole.UNKNOWN))
        label = str(raw_elem.get("label", "") or "")
        interaction = str(raw_elem.get("interaction", "none"))
        clickable = bool(raw_elem.get("clickable", False))
        scrollable = bool(raw_elem.get("scrollable", False))
        enabled = bool(raw_elem.get("enabled", True))
        is_explored = el_id in explored_set

        compact_elem = {
            "element_id": el_id,
            "role": role,
            "label": label,
            "interaction": interaction,
            "clickable": clickable,
            "scrollable": scrollable,
            "enabled": enabled,
            "explored": is_explored,
        }
        compact_elements.append(compact_elem)

        # Record as available interaction if actionable, enabled, unexplored, and not system UI
        if (
            not is_explored
            and enabled
            and interaction != "none"
            and not ActionSelector.is_system_element(el_id)
        ):
            available_interactions.append({
                "element_id": el_id,
                "role": role,
                "label": label,
                "interaction": interaction,
            })

    return ReasoningContext(
        screen_id=assigned_screen_id,
        screen_type=understanding.screen_type,
        likely_purpose=understanding.likely_purpose,
        current_activity=current_activity,
        elements=compact_elements,
        explored_element_ids=sorted(list(explored_set)),
        available_interactions=available_interactions,
        recent_actions=recent_actions,
        recent_screens=recent_screens,
        exploration_step=exploration_step,
    )


class BaseReasoner(ABC):
    """Abstract base class defining the reasoner interface."""

    @abstractmethod
    def decide(self, context: ReasoningContext) -> AgentAction:
        """
        Evaluates the ReasoningContext and decides the next AgentAction.

        :param context: Compact semantic ReasoningContext.
        :return: Standardized AgentAction.
        """
        pass


class RuleBasedReasoner(BaseReasoner):
    """
    Deterministic rule-based reasoner implementing strategic exploration
    heuristics without external LLM inference.
    """

    def __init__(
        self,
        safety_validator: Optional[SafetyValidator] = None,
        stop_on_screen_type: Optional[str] = None,
    ) -> None:
        self.safety_validator = safety_validator or SafetyValidator()
        self.stop_on_screen_type = stop_on_screen_type

    def compute_candidate_score(self, elem: Dict[str, Any]) -> int:
        """Computes priority score for candidate elements in ReasoningContext."""
        score = 0
        role = elem.get("role", ElementRole.UNKNOWN)
        label = str(elem.get("label", "") or "")
        el_id = str(elem.get("element_id", "") or "")

        # 1. Semantic role priority
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
            ElementRole.UNKNOWN: 5,
        }
        score += role_scores.get(role, 0)

        # 2. Label cues
        if label:
            score += 15
            lower_label = label.lower()
            intent_cues = (
                "search",
                "next",
                "continue",
                "sign in",
                "login",
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
            )
            if any(cue in lower_label for cue in intent_cues):
                score += 15

        # 3. Real ID
        if el_id and not el_id.startswith("elem_"):
            score += 10
            if ":id/" in el_id and not el_id.startswith("android:id/"):
                score += 5

        return score

    def decide(self, context: ReasoningContext) -> AgentAction:
        """
        Decides the next action based on semantic context:
        1. Checks for terminal stop conditions.
        2. Filters out system UI, explored elements, and potentially destructive actions.
        3. Ranks remaining candidates by semantic priority.
        4. Selects top candidate or falls back to 'back'.
        """
        # Terminal condition check
        if (
            self.stop_on_screen_type
            and context.screen_type == self.stop_on_screen_type
        ):
            return AgentAction(
                action="stop",
                reason=f"Reached terminal screen_type={self.stop_on_screen_type}",
            )

        # Filter valid, safe, unexplored candidates
        candidates = []
        for elem in context.elements:
            el_id = elem.get("element_id", "")
            if not el_id:
                continue
            if elem.get("explored"):
                continue
            if not elem.get("enabled"):
                continue
            if ActionSelector.is_system_element(el_id):
                continue

            # Safety filter: avoid destructive actions during exploration
            label = elem.get("label", "")
            if self.safety_validator.is_risky_text(label) or self.safety_validator.is_risky_text(el_id):
                continue

            interaction = elem.get("interaction", "none")
            if interaction in ("tap", "type", "scroll") or elem.get("clickable"):
                candidates.append(elem)

        if not candidates:
            return AgentAction(
                action="back",
                reason="No unexplored safe interactions available on screen",
            )

        # Deterministic ranking
        candidates.sort(key=self.compute_candidate_score, reverse=True)
        chosen = candidates[0]

        role = chosen.get("role", ElementRole.UNKNOWN)
        label = chosen.get("label", "")
        interaction = chosen.get("interaction", "tap")
        action_name = "tap" if interaction in ("tap", "none") else interaction

        if label:
            reason = f"semantic_role={role}; label={label}; unexplored"
        else:
            reason = f"semantic_role={role}; unexplored"

        return AgentAction(
            action=action_name,
            target=ActionTarget(element_id=chosen["element_id"]),
            reason=reason,
        )
