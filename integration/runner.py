"""
Integration Runner module.

Coordinates a single complete execution cycle between Android Controller and Exploration Agent:
OBSERVE -> ScreenState -> AGENT -> Action -> CONTROLLER -> ActionResult
"""

from typing import Any, Dict, Optional

try:
    from .adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
except (ImportError, ValueError):
    from adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )


class IntegrationRunner:
    """
    Coordinates a single observe-decide-act cycle between the Android Controller
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

    def run_cycle(self, screen_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute one complete integration loop cycle:
        1. OBSERVE: Obtain screen state from Controller and convert to API ScreenState.
        2. DECIDE: Pass ScreenState to Agent and convert decision to API Action.
        3. EXECUTE: Execute Action on Controller and capture resulting ActionResult.

        :param screen_id: Optional screen identifier hint for the Agent.
        :return: Standardized ActionResult dictionary conforming to API_CONTRACT.md.
        """
        if self.controller is None:
            raise ValueError("Android Controller is not configured.")
        if self.agent is None:
            raise ValueError("Exploration Agent is not configured.")

        # 1. OBSERVE
        raw_state = self.controller.get_current_state()
        screen_state = to_api_screen_state(raw_state)

        # 2. DECIDE
        # Provide screen_id to agent input if not explicitly set
        agent_input = dict(screen_state)
        assigned_screen_id = screen_id or screen_state.get("current_activity") or "screen_current"
        agent_input["screen_id"] = assigned_screen_id

        raw_agent_action = self.agent.step(agent_input)
        api_action = to_api_action(raw_agent_action)

        # Handle 'stop' action terminal signal
        if api_action.get("action") == "stop":
            return build_action_result(
                success=True,
                action=api_action,
                new_state=screen_state,
                error=None,
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
