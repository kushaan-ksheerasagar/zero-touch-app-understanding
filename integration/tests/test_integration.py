"""
Unit tests for Phase 2 Integration layer.

Tests:
A. Controller state is converted into API ScreenState correctly.
B. Agent action is converted into API Action correctly.
C. A controller -> agent -> controller cycle completes successfully.
D. Controller failure is represented as ActionResult with success=False and error.
E. Pure in-memory execution without requiring ADB or a live device.
"""

import os
import sys
import unittest
from typing import Any, Dict, Optional
from unittest.mock import MagicMock


# Configure sys.path for repo modules
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INTEGRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, INTEGRATION_DIR)

from adapters import (
    build_action_result,
    to_api_action,
    to_api_screen_state,
    to_controller_action,
)
from fingerprint import compute_screen_fingerprint
from runner import ExplorationResult, IntegrationRunner
from agent.agent import ExplorationAgent




class FakeController:
    """Mock Android Controller providing controllable state transitions without ADB."""

    def __init__(self, initial_state: Dict[str, Any], next_state: Optional[Dict[str, Any]] = None) -> None:
        self.current_state = initial_state
        self.next_state = next_state
        self.executed_actions = []
        self.should_fail = False
        self.failure_message = "Mock execution error"

    def get_current_state(self) -> Dict[str, Any]:
        return self.current_state

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self.executed_actions.append(action)
        if self.should_fail:
            raise ValueError(self.failure_message)
        if self.next_state:
            self.current_state = self.next_state
        return self.current_state


class TestAdapters(unittest.TestCase):
    """Test suite for adapter conversions (Test A & Test B)."""

    def test_to_api_screen_state_normalization(self) -> None:
        """Test A: Controller state is converted into the API ScreenState correctly."""
        raw_controller_state = {
            "screenshot_path": "screenshots/screen_001.png",
            "current_activity": "com.example.shop/.MainActivity",
            "elements": [
                {
                    "element_id": "com.example.shop:id/btn_search",
                    "type": "android.widget.ImageButton",
                    "text": "",
                    "content_description": "Search products",
                    "bounds": [920, 80, 1032, 160],
                    "center": [976, 120],
                    "clickable": True,
                    "scrollable": False,
                    "focusable": True,
                    "enabled": True,
                },
                {
                    "element_id": "elem_fallback_01",
                    "type": "TextView",
                    "text": "Featured Drops",
                    # bounds without explicit center
                    "bounds": [100, 200, 300, 400],
                    "clickable": False,
                }
            ]
        }

        api_state = to_api_screen_state(raw_controller_state)

        # Top-level checks
        self.assertEqual(api_state["screenshot_path"], "screenshots/screen_001.png")
        self.assertEqual(api_state["current_activity"], "com.example.shop/.MainActivity")
        self.assertEqual(len(api_state["elements"]), 2)

        # First element checks
        e1 = api_state["elements"][0]
        self.assertEqual(e1["element_id"], "com.example.shop:id/btn_search")
        self.assertEqual(e1["type"], "android.widget.ImageButton")
        self.assertEqual(e1["content_description"], "Search products")
        self.assertEqual(e1["bounds"], [920, 80, 1032, 160])
        self.assertEqual(e1["center"], [976, 120])
        self.assertTrue(e1["clickable"])
        self.assertTrue(e1["enabled"])

        # Second element checks (center calculated from bounds, defaults filled)
        e2 = api_state["elements"][1]
        self.assertEqual(e2["element_id"], "elem_fallback_01")
        self.assertEqual(e2["center"], [200, 300])
        self.assertFalse(e2["clickable"])
        self.assertFalse(e2["scrollable"])

    def test_to_api_action_conversion(self) -> None:
        """Test B: Agent action is converted into the API Action correctly."""
        # 1. Tap action
        raw_agent_action = {
            "action": "tap",
            "target": {
                "element_id": "com.example.shop:id/btn_login"
            }
        }
        api_action = to_api_action(raw_agent_action)
        self.assertEqual(api_action["action"], "tap")
        self.assertEqual(api_action["target"]["element_id"], "com.example.shop:id/btn_login")

        # 2. Type action with parameters
        raw_type_action = {
            "action": "type",
            "target": {"element_id": "input_search"},
            "parameters": {"text": "headphones"}
        }
        api_type = to_api_action(raw_type_action)
        self.assertEqual(api_type["action"], "type")
        self.assertEqual(api_type["parameters"]["text"], "headphones")

        # 3. Back action
        api_back = to_api_action({"action": "back"})
        self.assertEqual(api_back, {"action": "back"})

    def test_to_controller_action_mapping(self) -> None:
        """Verify mapping parameters to Controller expectations."""
        # Scroll with duration_ms
        api_scroll = {
            "action": "scroll",
            "parameters": {"direction": "down", "duration_ms": 500}
        }
        ctrl_scroll = to_controller_action(api_scroll)
        self.assertEqual(ctrl_scroll["direction"], "down")

        # Type action with parameters.text
        api_type = {
            "action": "type",
            "parameters": {"text": "hello"}
        }
        ctrl_type = to_controller_action(api_type)
        self.assertEqual(ctrl_type["text"], "hello")


class TestIntegrationRunner(unittest.TestCase):
    """Test suite for IntegrationRunner execution cycles (Test C, D, & E)."""

    def setUp(self) -> None:
        self.initial_screen = {
            "screenshot_path": "screenshots/screen_001.png",
            "current_activity": "com.example.shop/.MainActivity",
            "elements": [
                {
                    "element_id": "btn_search",
                    "type": "android.widget.Button",
                    "text": "Search",
                    "bounds": [100, 100, 400, 200],
                    "center": [250, 150],
                    "clickable": True,
                    "enabled": True,
                }
            ]
        }
        self.next_screen = {
            "screenshot_path": "screenshots/screen_002.png",
            "current_activity": "com.example.shop/.SearchActivity",
            "elements": [
                {
                    "element_id": "input_query",
                    "type": "android.widget.EditText",
                    "text": "",
                    "bounds": [50, 50, 500, 150],
                    "clickable": True,
                    "enabled": True,
                }
            ]
        }

    def test_complete_cycle_success(self) -> None:
        """Test C: Fake controller -> fake agent -> fake controller cycle completes successfully."""
        fake_controller = FakeController(self.initial_screen, self.next_screen)

        # Mock agent that chooses tap on btn_search
        mock_agent = MagicMock()
        mock_agent.step.return_value = {
            "action": "tap",
            "target": {"element_id": "btn_search"}
        }

        runner = IntegrationRunner(controller=fake_controller, agent=mock_agent)
        result = runner.run_cycle(screen_id="screen_home")

        # Verify cycle outcome conforming to API_CONTRACT.md
        self.assertTrue(result["success"])
        self.assertIsNone(result["error"])
        self.assertEqual(result["action_executed"]["action"], "tap")
        self.assertEqual(result["action_executed"]["element_id"], "btn_search")
        self.assertEqual(result["state"]["current_activity"], "com.example.shop/.SearchActivity")
        self.assertEqual(result["state"]["screenshot_path"], "screenshots/screen_002.png")

        # Verify Controller executed the action
        self.assertEqual(len(fake_controller.executed_actions), 1)
        self.assertEqual(fake_controller.executed_actions[0]["action"], "tap")

        # Verify Agent received ScreenState
        mock_agent.step.assert_called_once()
        agent_arg = mock_agent.step.call_args[0][0]
        self.assertEqual(agent_arg["screen_id"], "screen_home")
        self.assertEqual(len(agent_arg["elements"]), 1)

    def test_controller_failure_handling(self) -> None:
        """Test D: Controller failure is represented as ActionResult with success=False and an error."""
        fake_controller = FakeController(self.initial_screen)
        fake_controller.should_fail = True
        fake_controller.failure_message = "Element 'unknown_btn' not found on screen"

        mock_agent = MagicMock()
        mock_agent.step.return_value = {
            "action": "tap",
            "target": {"element_id": "unknown_btn"}
        }

        runner = IntegrationRunner(controller=fake_controller, agent=mock_agent)
        result = runner.run_cycle()

        self.assertFalse(result["success"])
        self.assertIn("Element 'unknown_btn' not found", result["error"])
        self.assertEqual(result["action_executed"]["action"], "tap")
        self.assertEqual(result["state"]["current_activity"], "com.example.shop/.MainActivity")

    def test_real_agent_integration(self) -> None:
        """Test using real ExplorationAgent implementation with FakeController."""
        fake_controller = FakeController(self.initial_screen, self.next_screen)
        agent = ExplorationAgent()

        runner = IntegrationRunner(controller=fake_controller, agent=agent)
        result = runner.run_cycle()

        self.assertTrue(result["success"])
        self.assertEqual(result["action_executed"]["action"], "tap")
        self.assertEqual(result["action_executed"]["element_id"], "btn_search")
        self.assertEqual(result["state"]["current_activity"], "com.example.shop/.SearchActivity")

    def test_terminal_stop_action(self) -> None:
        """Test that agent 'stop' action returns clean terminal result without calling controller."""
        fake_controller = FakeController(self.initial_screen)
        mock_agent = MagicMock()
        mock_agent.step.return_value = {"action": "stop"}

        runner = IntegrationRunner(controller=fake_controller, agent=mock_agent)
        result = runner.run_cycle()

        self.assertTrue(result["success"])
        self.assertEqual(result["action_executed"]["action"], "stop")
        self.assertIsNone(result["error"])
        self.assertEqual(len(fake_controller.executed_actions), 0)


class MultiStepFakeController:
    """Mock Android Controller providing multi-step state transitions without ADB."""

    def __init__(self, states: list) -> None:
        self.states = states
        self.index = 0
        self.executed_actions = []
        self.should_fail = False
        self.failure_message = "Mock execution error"

    def get_current_state(self) -> Dict[str, Any]:
        return self.states[min(self.index, len(self.states) - 1)]

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self.executed_actions.append(action)
        if self.should_fail:
            raise ValueError(self.failure_message)
        if self.index + 1 < len(self.states):
            self.index += 1
        return self.states[self.index]


class ScriptedFakeAgent:
    """Mock agent returning a pre-defined sequence of actions."""

    def __init__(self, actions: list) -> None:
        self.actions = actions
        self.index = 0
        self.received_screens = []

    def step(self, screen_data: Dict[str, Any]) -> Dict[str, Any]:
        self.received_screens.append(screen_data)
        if self.index < len(self.actions):
            act = self.actions[self.index]
            self.index += 1
            return act
        return {"action": "stop"}


class TestBoundedExploration(unittest.TestCase):
    """
    Test suite for bounded multi-step autonomous exploration (Phase 2.3).
    Covers Requirements A through G:
    A. max_steps=3 executes at most 3 actions.
    B. Multiple states are discovered.
    C. Transitions are recorded.
    D. stop terminates exploration.
    E. failed action is recorded safely.
    F. repeated state/action does not create an infinite loop.
    G. Same Activity with different UI state can produce different fingerprints.
    """

    def setUp(self) -> None:
        self.screen_home = {
            "screenshot_path": "screenshots/screen_001.png",
            "current_activity": "com.example.shop/.MainActivity",
            "elements": [
                {
                    "element_id": "btn_search",
                    "type": "android.widget.Button",
                    "text": "Search",
                    "bounds": [100, 100, 400, 200],
                    "clickable": True,
                    "enabled": True,
                },
                {
                    "element_id": "btn_cart",
                    "type": "android.widget.Button",
                    "text": "Cart",
                    "bounds": [500, 100, 800, 200],
                    "clickable": True,
                    "enabled": True,
                },
            ],
        }

        self.screen_search = {
            "screenshot_path": "screenshots/screen_002.png",
            "current_activity": "com.example.shop/.SearchActivity",
            "elements": [
                {
                    "element_id": "input_query",
                    "type": "android.widget.EditText",
                    "text": "",
                    "bounds": [50, 50, 500, 150],
                    "clickable": True,
                    "enabled": True,
                },
                {
                    "element_id": "btn_submit",
                    "type": "android.widget.Button",
                    "text": "Go",
                    "bounds": [520, 50, 700, 150],
                    "clickable": True,
                    "enabled": True,
                },
            ],
        }

        self.screen_results = {
            "screenshot_path": "screenshots/screen_003.png",
            "current_activity": "com.example.shop/.ResultsActivity",
            "elements": [
                {
                    "element_id": "item_first_result",
                    "type": "android.widget.TextView",
                    "text": "Wireless Headphones",
                    "bounds": [50, 200, 900, 350],
                    "clickable": True,
                    "enabled": True,
                }
            ],
        }

        self.screen_detail = {
            "screenshot_path": "screenshots/screen_004.png",
            "current_activity": "com.example.shop/.DetailActivity",
            "elements": [
                {
                    "element_id": "btn_buy_now",
                    "type": "android.widget.Button",
                    "text": "Buy Now",
                    "bounds": [100, 800, 900, 950],
                    "clickable": True,
                    "enabled": True,
                }
            ],
        }

    def test_max_steps_bounds_execution(self) -> None:
        """Test A: max_steps=3 executes at most 3 actions."""
        # 5 states available, 5 actions configured
        states = [
            self.screen_home,
            self.screen_search,
            self.screen_results,
            self.screen_detail,
            self.screen_home,
        ]
        actions = [
            {"action": "tap", "target": {"element_id": "btn_search"}},
            {"action": "tap", "target": {"element_id": "btn_submit"}},
            {"action": "tap", "target": {"element_id": "item_first_result"}},
            {"action": "tap", "target": {"element_id": "btn_buy_now"}},
            {"action": "back"},
        ]

        controller = MultiStepFakeController(states)
        agent = ScriptedFakeAgent(actions)
        runner = IntegrationRunner(controller=controller, agent=agent)

        result = runner.run_exploration(max_steps=3)

        self.assertIsInstance(result, ExplorationResult)
        self.assertEqual(len(result.steps), 3)
        self.assertEqual(len(controller.executed_actions), 3)
        self.assertEqual(result.termination_reason, "max_steps_reached")

    def test_multiple_states_discovered(self) -> None:
        """Test B: Multiple states are discovered across exploration steps."""
        states = [self.screen_home, self.screen_search, self.screen_results]
        actions = [
            {"action": "tap", "target": {"element_id": "btn_search"}},
            {"action": "tap", "target": {"element_id": "btn_submit"}},
        ]

        controller = MultiStepFakeController(states)
        agent = ScriptedFakeAgent(actions)
        runner = IntegrationRunner(controller=controller, agent=agent)

        result = runner.run_exploration(max_steps=2)

        # Discovered states should include initial home, search, and results screen
        self.assertGreaterEqual(len(result.discovered_states), 3)
        home_fp = compute_screen_fingerprint(self.screen_home)
        search_fp = compute_screen_fingerprint(self.screen_search)
        results_fp = compute_screen_fingerprint(self.screen_results)

        self.assertIn(home_fp, result.discovered_states)
        self.assertIn(search_fp, result.discovered_states)
        self.assertIn(results_fp, result.discovered_states)

    def test_transitions_recorded(self) -> None:
        """Test C: State transitions (source_state -> action -> destination_state) are recorded."""
        states = [self.screen_home, self.screen_search]
        actions = [{"action": "tap", "target": {"element_id": "btn_search"}}]

        controller = MultiStepFakeController(states)
        agent = ScriptedFakeAgent(actions)
        runner = IntegrationRunner(controller=controller, agent=agent)

        result = runner.run_exploration(max_steps=1)

        self.assertEqual(len(result.transitions), 1)
        transition = result.transitions[0]
        home_fp = compute_screen_fingerprint(self.screen_home)
        search_fp = compute_screen_fingerprint(self.screen_search)

        self.assertEqual(transition["source_state"], home_fp)
        self.assertEqual(transition["destination_state"], search_fp)
        self.assertEqual(transition["action"]["action"], "tap")
        self.assertEqual(transition["action"]["target"]["element_id"], "btn_search")
        self.assertTrue(transition["success"])
        self.assertIsNone(transition["error"])

    def test_stop_action_terminates_exploration(self) -> None:
        """Test D: 'stop' action terminates exploration cleanly before max_steps."""
        states = [self.screen_home, self.screen_search]
        actions = [
            {"action": "tap", "target": {"element_id": "btn_search"}},
            {"action": "stop"},
            {"action": "tap", "target": {"element_id": "btn_submit"}},
        ]

        controller = MultiStepFakeController(states)
        agent = ScriptedFakeAgent(actions)
        runner = IntegrationRunner(controller=controller, agent=agent)

        result = runner.run_exploration(max_steps=10)

        # Should terminate at step 2 upon seeing 'stop'
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(result.termination_reason, "agent_stopped")
        # Controller only executed the first tap action, not the stop action
        self.assertEqual(len(controller.executed_actions), 1)

    def test_failed_action_recorded_safely(self) -> None:
        """Test E: Failed action is recorded safely without crashing."""
        controller = MultiStepFakeController([self.screen_home])
        controller.should_fail = True
        controller.failure_message = "Element not clickable"

        actions = [{"action": "tap", "target": {"element_id": "btn_search"}}]
        agent = ScriptedFakeAgent(actions)
        runner = IntegrationRunner(controller=controller, agent=agent)

        result = runner.run_exploration(max_steps=5)

        self.assertEqual(len(result.steps), 1)
        step = result.steps[0]
        self.assertFalse(step["action_result"]["success"])
        self.assertIn("Element not clickable", step["action_result"]["error"])
        self.assertEqual(result.termination_reason, "action_failed")
        self.assertFalse(result.transitions[0]["success"])
        self.assertIn("Element not clickable", result.transitions[0]["error"])

    def test_repeated_state_action_prevents_infinite_loop(self) -> None:
        """Test F: Repeated state/action combination avoids infinite loops and terminates cleanly."""
        # Static screen where controller never changes state
        static_controller = FakeController(self.screen_home)
        # Agent that repeatedly returns the exact same action
        mock_agent = MagicMock()
        mock_agent.step.return_value = {
            "action": "tap",
            "target": {"element_id": "btn_search"},
        }

        runner = IntegrationRunner(controller=static_controller, agent=mock_agent)
        result = runner.run_exploration(max_steps=10)

        # Step 1 executes successfully.
        # Step 2 detects repeated state + action, safely aborts, and terminates.
        self.assertEqual(result.termination_reason, "repeated_state_action")
        self.assertEqual(len(result.steps), 2)
        # Verify controller was called only once (the duplicate action was not executed)
        self.assertEqual(len(static_controller.executed_actions), 1)
        self.assertFalse(result.steps[1]["action_result"]["success"])
        self.assertIn("Repeated state and action", result.steps[1]["action_result"]["error"])

    def test_fingerprint_same_activity_different_ui_state(self) -> None:
        """Test G: Same Activity with different UI state produces different fingerprints."""
        screen_v1 = {
            "current_activity": "com.android.settings/.Settings",
            "elements": [
                {
                    "element_id": "com.android.settings:id/wifi",
                    "type": "android.widget.TextView",
                    "text": "Wi-Fi",
                    "clickable": True,
                }
            ],
        }
        screen_v2 = {
            "current_activity": "com.android.settings/.Settings",
            "elements": [
                {
                    "element_id": "com.android.settings:id/bluetooth",
                    "type": "android.widget.TextView",
                    "text": "Bluetooth",
                    "clickable": True,
                }
            ],
        }
        screen_v3 = {
            "current_activity": "com.android.settings/.Settings",
            "elements": [
                {
                    "element_id": "com.android.settings:id/wifi",
                    "type": "android.widget.TextView",
                    "text": "Wi-Fi",
                    "clickable": True,
                }
            ],
        }

        fp1 = compute_screen_fingerprint(screen_v1)
        fp2 = compute_screen_fingerprint(screen_v2)
        fp3 = compute_screen_fingerprint(screen_v3)

        # Same activity, different UI elements -> different fingerprints
        self.assertNotEqual(fp1, fp2)
        # Same activity, identical UI elements -> exact same deterministic fingerprint
        self.assertEqual(fp1, fp3)

    def test_exploration_with_real_agent(self) -> None:
        """Test end-to-end multi-step exploration with real ExplorationAgent."""
        states = [self.screen_home, self.screen_search]
        controller = MultiStepFakeController(states)
        real_agent = ExplorationAgent()

        runner = IntegrationRunner(controller=controller, agent=real_agent)
        result = runner.run_exploration(max_steps=2)

        self.assertEqual(len(result.steps), 2)
        self.assertTrue(result.steps[0]["action_result"]["success"])
        self.assertGreaterEqual(len(result.discovered_states), 2)
        self.assertEqual(len(result.transitions), 2)


if __name__ == "__main__":
    unittest.main()

