"""
Mocked unit tests for Gemini + Android integration.

Verifies end-to-end integration flow without calling real Gemini APIs,
without ADB, and without physical devices.
"""

import os
import sys
import unittest
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INTEGRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, INTEGRATION_DIR)

from agent.agent import ExplorationAgent
from agent.gemini_client import GeminiLLMClient
from agent.llm_reasoner import LLMReasoner
from agent.safety import SafetyValidator
from integration.adapters import to_api_screen_state
from integration.fingerprint import compute_screen_fingerprint
from integration.runner import IntegrationRunner


class FakeAndroidController:
    """In-memory mock AndroidController for offline testing."""

    def __init__(self, initial_state: Dict[str, Any], next_state: Optional[Dict[str, Any]] = None) -> None:
        self.current_state = initial_state
        self.next_state = next_state
        self.executed_actions = []
        self.connected = False

    def connect(self, device_id: Optional[str] = None) -> str:
        self.connected = True
        return device_id or "emulator-5554"

    def launch_app(self, package: str, activity: Optional[str] = None) -> Dict[str, Any]:
        return self.current_state

    def get_current_state(self) -> Dict[str, Any]:
        return self.current_state

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self.executed_actions.append(action)
        if self.next_state:
            self.current_state = self.next_state
        return self.current_state


class TestGeminiAndroidIntegration(unittest.TestCase):
    """Test suite for Gemini reasoning connected to Android execution."""

    def setUp(self) -> None:
        self.state_screen_1 = {
            "screenshot_path": "screenshots/screen_1.png",
            "current_activity": "com.android.settings.SettingsActivity",
            "elements": [
                {
                    "element_id": "com.android.settings:id/network",
                    "type": "android.widget.TextView",
                    "text": "Network & internet",
                    "content_description": "Network settings",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "bounds": [0, 100, 1080, 250],
                    "center": [540, 175],
                },
                {
                    "element_id": "com.android.settings:id/display",
                    "type": "android.widget.TextView",
                    "text": "Display",
                    "content_description": "Display settings",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "bounds": [0, 250, 1080, 400],
                    "center": [540, 325],
                },
            ],
        }

        self.state_screen_2 = {
            "screenshot_path": "screenshots/screen_2.png",
            "current_activity": "com.android.settings.network.NetworkDashboardActivity",
            "elements": [
                {
                    "element_id": "com.android.settings:id/wifi_toggle",
                    "type": "android.widget.Switch",
                    "text": "Wi-Fi",
                    "content_description": "Wi-Fi toggle",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "bounds": [0, 100, 1080, 250],
                    "center": [540, 175],
                }
            ],
        }

    def test_gemini_reasoner_cycle_with_fake_controller(self) -> None:
        """Verify full cycle: ScreenState -> Gemini decision -> safety -> controller execution."""
        mock_raw_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "tap", "target": {"element_id": "com.android.settings:id/network"}, "reason": "explore network settings"}'
        mock_raw_gemini.models.generate_content.return_value = mock_response

        gemini_client = GeminiLLMClient(client=mock_raw_gemini)
        reasoner = LLMReasoner(client=gemini_client)
        agent = ExplorationAgent(reasoner=reasoner)
        controller = FakeAndroidController(self.state_screen_1, self.state_screen_2)

        runner = IntegrationRunner(controller=controller, agent=agent)

        # 1. Capture initial fingerprint
        initial_api_state = to_api_screen_state(controller.get_current_state())
        initial_fp = compute_screen_fingerprint(initial_api_state)

        # 2. Run cycle
        result = runner.run_cycle()

        # 3. Assertions
        self.assertTrue(result["success"])
        self.assertEqual(len(controller.executed_actions), 1)
        executed = controller.executed_actions[0]
        self.assertEqual(executed["action"], "tap")
        self.assertEqual(executed["target"]["element_id"], "com.android.settings:id/network")

        # 4. Fingerprint changed check
        resulting_api_state = result["state"]
        resulting_fp = compute_screen_fingerprint(resulting_api_state)
        self.assertNotEqual(initial_fp, resulting_fp)

    def test_gemini_destructive_action_blocked_by_safety(self) -> None:
        """Verify safety validator intercepts destructive actions before controller execution."""
        mock_raw_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "tap", "target": {"element_id": "com.app:id/btn_delete_all"}, "reason": "delete user data"}'
        mock_raw_gemini.models.generate_content.return_value = mock_response

        gemini_client = GeminiLLMClient(client=mock_raw_gemini)
        reasoner = LLMReasoner(client=gemini_client)
        safety = SafetyValidator()
        agent = ExplorationAgent(reasoner=reasoner, safety_validator=safety)
        controller = FakeAndroidController(self.state_screen_1)

        runner = IntegrationRunner(controller=controller, agent=agent)
        result = runner.run_cycle()

        # Action should be fallen back to 'back' instead of deleting data
        self.assertTrue(result["success"])
        executed = controller.executed_actions[0]
        self.assertEqual(executed["action"], "back")

    def test_gemini_hallucinated_element_falls_back(self) -> None:
        """Verify hallucinated element ID returns safe 'back' action."""
        mock_raw_gemini = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "tap", "target": {"element_id": "com.invented:id/ghost_button"}, "reason": "invented element"}'
        mock_raw_gemini.models.generate_content.return_value = mock_response

        gemini_client = GeminiLLMClient(client=mock_raw_gemini)
        reasoner = LLMReasoner(client=gemini_client)
        agent = ExplorationAgent(reasoner=reasoner)
        controller = FakeAndroidController(self.state_screen_1)

        runner = IntegrationRunner(controller=controller, agent=agent)
        result = runner.run_cycle()

        self.assertTrue(result["success"])
        executed = controller.executed_actions[0]
        self.assertEqual(executed["action"], "back")


if __name__ == "__main__":
    unittest.main()
