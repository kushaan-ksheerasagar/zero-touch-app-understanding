"""
Integration Runner module.

Coordinates execution cycles between Android Controller and Exploration Agent:
OBSERVE -> ScreenState -> AGENT -> Action -> CONTROLLER -> ActionResult

Provides bounded multi-step autonomous exploration:
OBSERVE -> DECIDE -> EXECUTE -> OBSERVE AGAIN -> REMEMBER -> REPEAT
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from .adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from .fingerprint import compute_screen_fingerprint
except (ImportError, ValueError):
    from adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from fingerprint import compute_screen_fingerprint


def _serialize_action(action: Dict[str, Any]) -> str:
    """Deterministic string signature of an action for loop detection."""
    action_type = str(action.get("action", "")).lower().strip()
    target = action.get("target") or {}
    el_id = str(target.get("element_id", "") or "").strip()
    coords = target.get("coordinates")
    coords_str = (
        f"{coords[0]},{coords[1]}"
        if isinstance(coords, (list, tuple)) and len(coords) == 2
        else ""
    )
    params = action.get("parameters") or {}
    text = str(params.get("text", "") or "").strip()
    direction = str(params.get("direction", "") or "").strip()
    return f"{action_type}:{el_id}:{coords_str}:{text}:{direction}"


@dataclass
class ExplorationResult:
    """
    Structured result of a bounded multi-step autonomous exploration run.
    """
    steps: List[Dict[str, Any]] = field(default_factory=list)
    discovered_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    termination_reason: str = "max_steps_reached"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result into a standard dictionary."""
        return {
            "steps": self.steps,
            "discovered_states": self.discovered_states,
            "transitions": self.transitions,
            "termination_reason": self.termination_reason,
        }

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class IntegrationRunner:
    """
    Coordinates observe-decide-act cycles between the Android Controller
    and the Exploration Agent through the standardized API contract.
    """

    def __init__(self, controller: Any = None, agent: Any = None) -> None:
        """
        Initialize runner with dependency injection.

        :param controller: AndroidController instance or mock/fake.
        :param agent: ExplorationAgent instance or mock/fake.
        """
        self.controller = controller
        self.agent = agent
        self.last_observed_state: Optional[Dict[str, Any]] = None
        self.last_api_action: Optional[Dict[str, Any]] = None
        self.last_screen_fingerprint: Optional[str] = None

    def run_cycle(
        self,
        screen_id: Optional[str] = None,
        seen_actions: Optional[Set[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute one complete integration loop cycle:
        1. OBSERVE: Obtain screen state from Controller and convert to API ScreenState.
        2. DECIDE: Pass ScreenState to Agent and convert decision to API Action.
        3. EXECUTE: Execute Action on Controller and capture resulting ActionResult.

        :param screen_id: Optional screen identifier hint for the Agent.
                          Defaults to deterministic screen fingerprint.
        :param seen_actions: Optional set of (screen_fingerprint, action_signature)
                             tuples already executed in the current exploration run.
                             If provided and the decided action matches, execution is aborted
                             to avoid infinite loops.
        :return: Standardized ActionResult dictionary conforming to API_CONTRACT.md.
        """
        if self.controller is None:
            raise ValueError("Android Controller is not configured.")
        if self.agent is None:
            raise ValueError("Exploration Agent is not configured.")

        # 1. OBSERVE
        raw_state = self.controller.get_current_state()
        screen_state = to_api_screen_state(raw_state)
        fingerprint = compute_screen_fingerprint(screen_state)
        assigned_screen_id = screen_id or fingerprint

        self.last_observed_state = screen_state
        self.last_screen_fingerprint = assigned_screen_id

        # 2. DECIDE
        # Provide screen_id to agent input
        agent_input = dict(screen_state)
        agent_input["screen_id"] = assigned_screen_id

        raw_agent_action = self.agent.step(agent_input)
        api_action = to_api_action(raw_agent_action)
        self.last_api_action = api_action

        # Handle 'stop' action terminal signal
        if api_action.get("action") == "stop":
            return build_action_result(
                success=True,
                action=api_action,
                new_state=screen_state,
                error=None,
            )

        # Loop prevention: check if this state-action pair was already executed
        action_sig = _serialize_action(api_action)
        if seen_actions is not None and (assigned_screen_id, action_sig) in seen_actions:
            return build_action_result(
                success=False,
                action=api_action,
                new_state=screen_state,
                error="Repeated state and action detected",
            )

        # 3. EXECUTE
        ctrl_action = to_controller_action(api_action)
        try:
            new_raw_state = self.controller.execute_action(ctrl_action)
            action_result = build_action_result(
                success=True,
                action=api_action,
                new_state=new_raw_state,
                error=None,
            )
        except Exception as exc:
            action_result = build_action_result(
                success=False,
                action=api_action,
                new_state=screen_state,
                error=str(exc),
            )

        return action_result

    def run_exploration(self, max_steps: int = 5) -> ExplorationResult:
        """
        Execute a bounded multi-step autonomous exploration loop:
        OBSERVE -> DECIDE -> EXECUTE -> OBSERVE AGAIN -> REMEMBER -> REPEAT

        :param max_steps: Maximum number of actions to execute during exploration.
        :return: ExplorationResult containing steps, discovered states, transitions,
                 and termination reason.
        """
        if self.controller is None:
            raise ValueError("Android Controller is not configured.")
        if self.agent is None:
            raise ValueError("Exploration Agent is not configured.")

        steps: List[Dict[str, Any]] = []
        discovered_states: Dict[str, Dict[str, Any]] = {}
        transitions: List[Dict[str, Any]] = []
        seen_state_actions: Set[Tuple[str, str]] = set()

        if max_steps <= 0:
            return ExplorationResult(
                steps=steps,
                discovered_states=discovered_states,
                transitions=transitions,
                termination_reason="max_steps_reached",
            )

        termination_reason = "max_steps_reached"

        for step_idx in range(1, max_steps + 1):
            action_result = self.run_cycle(seen_actions=seen_state_actions)

            observed_state = self.last_observed_state or {}
            api_action = self.last_api_action or {}
            src_fp = self.last_screen_fingerprint or compute_screen_fingerprint(observed_state)

            resulting_state = action_result.get("state", {})
            dst_fp = compute_screen_fingerprint(resulting_state)

            # Record discovered states
            if src_fp not in discovered_states:
                discovered_states[src_fp] = observed_state
            if dst_fp not in discovered_states:
                discovered_states[dst_fp] = resulting_state

            # Action serialization for state-action pair tracking
            action_sig = _serialize_action(api_action)
            state_action_pair = (src_fp, action_sig)

            # Record transition
            transition = {
                "source_state": src_fp,
                "destination_state": dst_fp,
                "source_screen_id": src_fp,
                "destination_screen_id": dst_fp,
                "action": api_action,
                "success": bool(action_result.get("success", False)),
                "error": action_result.get("error"),
            }
            transitions.append(transition)

            # Record step
            step_record = {
                "step_number": step_idx,
                "observed_state": observed_state,
                "action": api_action,
                "action_result": action_result,
                "resulting_state": resulting_state,
                "source_state": src_fp,
                "destination_state": dst_fp,
            }
            steps.append(step_record)

            # Check termination conditions:
            # 1. Action was aborted because of repeated state-action
            if action_result.get("error") == "Repeated state and action detected":
                termination_reason = "repeated_state_action"
                break

            # 2. Agent requested 'stop'
            if api_action.get("action") == "stop":
                termination_reason = "agent_stopped"
                break

            # 3. Action execution failed
            if not action_result.get("success", False):
                termination_reason = "action_failed"
                break

            seen_state_actions.add(state_action_pair)

        return ExplorationResult(
            steps=steps,
            discovered_states=discovered_states,
            transitions=transitions,
            termination_reason=termination_reason,
        )
