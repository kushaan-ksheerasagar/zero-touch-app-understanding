"""
Unit tests for Autonomous Multi-Step Exploration Engine.

Validates the full observe-understand-decide-validate-act-remember loop
using deterministic mocks (no real Gemini, ADB, or emulator required).
"""

import json
import os
import shutil
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

from agent.agent import ExplorationAgent
from agent.llm_reasoner import FakeLLMClient, LLMReasoner
from agent.memory import ExplorationMemory
from agent.safety import SafetyValidator
from integration.explorer import AutonomousExplorer
from knowledge.builder import KnowledgeBuilder


class FakeAndroidController:
    """Mock controller returning controlled sequence of screen states."""

    def __init__(self, screens: List[Dict[str, Any]]) -> None:
        self.screens = screens
        self.screen_idx = 0
        self.executed_actions: List[Dict[str, Any]] = []

    def get_current_state(self) -> Dict[str, Any]:
        idx = min(self.screen_idx, len(self.screens) - 1)
        return dict(self.screens[idx])

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self.executed_actions.append(action)
        action_name = action.get("action", "")
        # Advance screen on successful forward action (like tap)
        if action_name == "tap" and self.screen_idx < len(self.screens) - 1:
            self.screen_idx += 1
        elif action_name == "back" and self.screen_idx > 0:
            self.screen_idx -= 1
        return self.get_current_state()


class TestAutonomousExploration(unittest.TestCase):
    """Test suite covering the 10 core autonomous exploration requirements."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.artifacts_path = os.path.join(self.test_dir, "artifacts", "app_knowledge_pack.json")

        self.screen_main = {
            "current_activity": "com.example.app/.MainActivity",
            "screenshot_path": "screenshots/main.png",
            "elements": [
                {
                    "element_id": "com.example.app:id/btn_network",
                    "type": "android.widget.Button",
                    "text": "Network & Internet",
                    "clickable": True,
                    "enabled": True,
                    "bounds": [100, 200, 500, 300],
                },
                {
                    "element_id": "com.example.app:id/btn_display",
                    "type": "android.widget.Button",
                    "text": "Display Settings",
                    "clickable": True,
                    "enabled": True,
                    "bounds": [100, 350, 500, 450],
                },
                {
                    "element_id": "com.example.app:id/btn_delete_data",
                    "type": "android.widget.Button",
                    "text": "Delete All Data",
                    "clickable": True,
                    "enabled": True,
                    "bounds": [100, 500, 500, 600],
                },
            ],
        }

        self.screen_network = {
            "current_activity": "com.example.app/.NetworkActivity",
            "screenshot_path": "screenshots/network.png",
            "elements": [
                {
                    "element_id": "com.example.app:id/btn_wifi",
                    "type": "android.widget.Button",
                    "text": "Wi-Fi Settings",
                    "clickable": True,
                    "enabled": True,
                    "bounds": [100, 200, 500, 300],
                },
            ],
        }

        self.screen_display = {
            "current_activity": "com.example.app/.DisplayActivity",
            "screenshot_path": "screenshots/display.png",
            "elements": [
                {
                    "element_id": "com.example.app:id/btn_brightness",
                    "type": "android.widget.Button",
                    "text": "Brightness Level",
                    "clickable": True,
                    "enabled": True,
                    "bounds": [100, 200, 500, 300],
                },
            ],
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _build_explorer(
        self,
        screens: List[Dict[str, Any]],
        responses: List[Dict[str, Any]],
        max_steps: int = 5,
        max_consecutive_backs: int = 3,
    ) -> Tuple[AutonomousExplorer, FakeAndroidController, ExplorationAgent]:
        controller = FakeAndroidController(screens)
        client = FakeLLMClient(responses)
        safety = SafetyValidator()
        reasoner = LLMReasoner(client=client, safety_validator=safety)
        memory = ExplorationMemory()
        agent = ExplorationAgent(reasoner=reasoner, memory=memory, safety_validator=safety)
        builder = KnowledgeBuilder(app_name="TestApp", package_name="com.example.app")

        explorer = AutonomousExplorer(
            controller=controller,
            agent=agent,
            knowledge_builder=builder,
            max_steps=max_steps,
            max_consecutive_backs=max_consecutive_backs,
            package_name="com.example.app",
            artifacts_path=self.artifacts_path,
            verbose=False,
        )
        return explorer, controller, agent

    # Requirement 1: Multi-step exploration
    def test_multi_step_exploration(self) -> None:
        """Verify multiple exploration steps execute in sequence."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Explore network"},
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_wifi"}, "reason": "Explore wifi"},
        ]
        explorer, controller, _ = self._build_explorer(
            screens=[self.screen_main, self.screen_network],
            responses=responses,
            max_steps=2,
        )
        summary = explorer.run()

        self.assertEqual(summary["steps_count"], 2)
        self.assertEqual(len(controller.executed_actions), 2)
        self.assertEqual(summary["successful_actions"], 2)
        self.assertEqual(summary["failed_actions"], 0)

    # Requirement 2: Screen discovery
    def test_screen_discovery(self) -> None:
        """Verify new screens are discovered and ingested."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Explore network"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[self.screen_main, self.screen_network],
            responses=responses,
            max_steps=1,
        )
        summary = explorer.run()

        self.assertGreaterEqual(summary["discovered_screens_count"], 2)
        self.assertGreaterEqual(summary["unique_screens_count"], 2)

    # Requirement 3: Transition recording
    def test_transition_recording(self) -> None:
        """Verify state transitions are correctly recorded with action and status."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Explore network"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[self.screen_main, self.screen_network],
            responses=responses,
            max_steps=1,
        )
        summary = explorer.run()

        self.assertEqual(summary["transitions_count"], 1)
        transition = explorer.knowledge_builder.pack.transitions[0]
        self.assertEqual(transition.action.action_type, "tap")
        self.assertEqual(transition.action.target_element_id, "com.example.app:id/btn_network")
        self.assertEqual(transition.status, "success")

    # Requirement 4: Duplicate screen detection
    def test_duplicate_screen_detection(self) -> None:
        """Verify returning to an already visited screen does not create duplicate screens."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Go network"},
            {"action": "back", "reason": "Return to main"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[self.screen_main, self.screen_network],
            responses=responses,
            max_steps=2,
        )
        summary = explorer.run()

        self.assertEqual(summary["steps_count"], 2)
        # Unique screens in Knowledge Pack must be exactly 2 (main and network)
        self.assertEqual(summary["unique_screens_count"], 2)

    # Requirement 5: Repeated-action loop prevention
    def test_repeated_action_prevention(self) -> None:
        """Verify attempting the same element on the same screen triggers loop prevention (back)."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "First tap"},
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Duplicate tap"},
        ]
        # Controller stays on screen_main
        explorer, controller, _ = self._build_explorer(
            screens=[self.screen_main],
            responses=responses,
            max_steps=2,
        )
        summary = explorer.run()

        self.assertEqual(summary["steps_count"], 2)
        # Step 1 was tap; Step 2 was intercepted by loop prevention and converted to 'back'
        self.assertEqual(controller.executed_actions[0]["action"], "tap")
        self.assertEqual(controller.executed_actions[1]["action"], "back")

    # Requirement 6: Hallucinated target handling
    def test_hallucinated_target_handling(self) -> None:
        """Verify non-existent element IDs safely fall back to 'back' without crashing."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/hallucinated_btn"}, "reason": "Imaginary button"},
        ]
        explorer, controller, _ = self._build_explorer(
            screens=[self.screen_main],
            responses=responses,
            max_steps=1,
        )
        summary = explorer.run()

        self.assertEqual(summary["steps_count"], 1)
        self.assertEqual(controller.executed_actions[0]["action"], "back")
        self.assertEqual(summary["successful_actions"], 1)

    # Requirement 7: Safety-blocked action
    def test_safety_blocked_action(self) -> None:
        """Verify destructive actions are blocked by safety validator and recorded."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_delete_data"}, "reason": "delete user data"},
        ]
        explorer, controller, _ = self._build_explorer(
            screens=[self.screen_main],
            responses=responses,
            max_steps=1,
        )
        summary = explorer.run()

        self.assertEqual(summary["safety_blocked_actions"], 1)
        self.assertEqual(controller.executed_actions[0]["action"], "back")

    # Requirement 8: Max-step termination
    def test_max_step_termination(self) -> None:
        """Verify exploration halts when max_steps is reached."""
        responses = [
            {"action": "wait", "reason": "Wait step"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[self.screen_main],
            responses=responses,
            max_steps=3,
        )
        summary = explorer.run()

        self.assertEqual(summary["steps_count"], 3)
        self.assertEqual(summary["termination_reason"], "max_steps_reached")

    # Requirement 9: KnowledgeBuilder integration and JSON export
    def test_knowledge_builder_integration(self) -> None:
        """Verify KnowledgeBuilder produces valid app_knowledge_pack.json artifact."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Explore"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[self.screen_main, self.screen_network],
            responses=responses,
            max_steps=1,
        )
        summary = explorer.run()

        self.assertTrue(os.path.exists(self.artifacts_path))
        with open(self.artifacts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("package_name"), "com.example.app")
        self.assertIn("screens", data)
        self.assertIn("transitions", data)
        self.assertGreaterEqual(len(data["screens"]), 1)

    # Requirement 10: Clean termination on stop action
    def test_clean_termination_on_stop_action(self) -> None:
        """Verify agent 'stop' decision cleanly halts exploration."""
        responses = [
            {"action": "tap", "target": {"element_id": "com.example.app:id/btn_network"}, "reason": "Explore"},
            {"action": "stop", "reason": "Exploration complete"},
            {"action": "wait", "reason": "Should not be executed"},
        ]
        explorer, controller, _ = self._build_explorer(
            screens=[self.screen_main, self.screen_network],
            responses=responses,
            max_steps=5,
        )
        summary = explorer.run()

        self.assertEqual(summary["steps_count"], 1)
        self.assertEqual(summary["termination_reason"], "agent_stopped")
        self.assertEqual(len(controller.executed_actions), 1)

    # Requirement 11: Max consecutive backs termination
    def test_max_consecutive_backs_termination(self) -> None:
        """Verify repeated consecutive backs cleanly terminate without endless loop."""
        responses = [
            {"action": "back", "reason": "Back 1"},
            {"action": "back", "reason": "Back 2"},
            {"action": "back", "reason": "Back 3"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[self.screen_main],
            responses=responses,
            max_steps=10,
            max_consecutive_backs=2,
        )
        summary = explorer.run()
        self.assertEqual(summary["termination_reason"], "max_consecutive_backs_reached")

    # Requirement 12: Semantic consistency and transition integrity
    def test_semantic_consistency_and_transitions_integrity(self) -> None:
        """Verify generated Knowledge Pack has pure 1:1 element semantics and intact transitions."""
        from knowledge.builder import validate_knowledge_pack

        screen_with_shared_ids = {
            "current_activity": "com.android.settings/.Settings",
            "screenshot_path": "screenshots/settings.png",
            "elements": [
                {
                    "element_id": "android:id/title",
                    "type": "android.widget.TextView",
                    "text": "Network & internet",
                    "bounds": [100, 100, 600, 200],
                },
                {
                    "element_id": "android:id/title",
                    "type": "android.widget.TextView",
                    "text": "Connected devices",
                    "bounds": [100, 220, 600, 320],
                },
                {
                    "element_id": "android:id/title",
                    "type": "android.widget.TextView",
                    "text": "Sound & vibration",
                    "bounds": [100, 340, 600, 440],
                },
                {
                    "element_id": "android:id/icon",
                    "type": "android.widget.ImageView",
                    "text": "",
                    "content_description": "Search settings",
                    "bounds": [900, 50, 1000, 150],
                },
            ],
        }
        screen_sub = {
            "current_activity": "com.android.settings/.SubSettings",
            "screenshot_path": "screenshots/sub.png",
            "elements": [
                {
                    "element_id": "android:id/title",
                    "type": "android.widget.TextView",
                    "text": "Wi-Fi",
                    "bounds": [100, 100, 600, 200],
                }
            ],
        }

        responses = [
            {"action": "tap", "target": {"element_id": "android:id/title"}, "reason": "Open Network & internet"},
        ]
        explorer, _, _ = self._build_explorer(
            screens=[screen_with_shared_ids, screen_sub],
            responses=responses,
            max_steps=1,
        )
        summary = explorer.run()

        with open(self.artifacts_path, "r", encoding="utf-8") as f:
            pack_data = json.load(f)

        # Validate with comprehensive integrity validator
        val_res = validate_knowledge_pack(pack_data)
        self.assertTrue(val_res["valid"], f"Validation failed: {val_res}")
        self.assertEqual(len(val_res["element_errors"]), 0)
        self.assertEqual(len(val_res["transition_errors"]), 0)

        # Check the elements of the first screen individually
        root_screen = list(pack_data["screens"].values())[0]
        elements = root_screen["elements"]
        self.assertEqual(len(elements), 4)

        # Verify exact 1:1 derived semantic labels
        self.assertIn("label=Network & internet", elements[0]["purpose"])
        self.assertIn("label=Connected devices", elements[1]["purpose"])
        self.assertIn("label=Sound & vibration", elements[2]["purpose"])
        self.assertIn("label=Search settings", elements[3]["purpose"])

        # Verify transitions serialized at top-level and in navigation_graph
        self.assertIn("transitions", pack_data)
        self.assertEqual(len(pack_data["transitions"]), 1)
        self.assertIn("transitions", pack_data["navigation_graph"])
        self.assertEqual(len(pack_data["navigation_graph"]["transitions"]), 1)
        self.assertEqual(pack_data["transitions"][0]["status"], "success")


if __name__ == "__main__":
    unittest.main()
