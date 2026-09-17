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
from runner import IntegrationRunner
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


if __name__ == "__main__":
    unittest.main()
