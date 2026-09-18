"""
Unit tests for semantic action selection (Phase 3.2).

Tests:
A. Semantic button is prioritized over generic clickable container.
B. Navigation element receives meaningful priority.
C. Text input is recognized as a semantic interaction.
D. Switch/checkbox/radio remain explorable.
E. System UI elements remain rejected.
F. Already attempted elements remain excluded.
G. Multiple meaningful controls are explored systematically rather than only one.
H. Unknown elements do not outrank meaningful semantic controls.
I. Existing selector tests remain passing.
J. Existing Agent tests remain passing.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.agent import ExplorationAgent
from agent.memory import ExplorationMemory
from agent.selector import ActionSelector
from agent.semantic import ElementRole


class TestSelectorSemantics(unittest.TestCase):
    """Test suite for semantic priority and systematic exploration."""

    def setUp(self) -> None:
        self.selector = ActionSelector()
        self.memory = ExplorationMemory()

    def test_button_prioritized_over_generic_clickable_container(self) -> None:
        """Test A: Semantic button is prioritized over generic clickable container."""
        elements = [
            # Generic clickable container with no label
            {
                "element_id": "elem_001_FrameLayout",
                "type": "android.widget.FrameLayout",
                "clickable": True,
            },
            # Real application button with action label
            {
                "element_id": "com.example.app:id/btn_continue",
                "type": "android.widget.Button",
                "text": "Continue",
                "clickable": True,
            },
        ]
        action = self.selector.select_action("screen_1", elements, self.memory)
        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.example.app:id/btn_continue")
        self.assertIsNotNone(action.reason)
        self.assertIn("semantic_role=button", action.reason)
        self.assertIn("label=Continue", action.reason)

    def test_navigation_element_receives_meaningful_priority(self) -> None:
        """Test B: Navigation element receives high meaningful priority."""
        elements = [
            {
                "element_id": "elem_card_unknown",
                "type": "android.widget.FrameLayout",
                "clickable": True,
            },
            {
                "element_id": "com.example.app:id/tab_explore",
                "type": "android.widget.TabWidget",
                "text": "Explore",
                "clickable": True,
            },
        ]
        action = self.selector.select_action("screen_1", elements, self.memory)
        self.assertEqual(action.target.element_id, "com.example.app:id/tab_explore")
        self.assertIn("semantic_role=navigation", action.reason)

    def test_text_input_recognized_as_semantic_interaction(self) -> None:
        """Test C: Text input is recognized as a semantic interaction."""
        input_elem = {
            "element_id": "com.example.app:id/input_search",
            "type": "android.widget.EditText",
            "text": "",
            "content_description": "Search query",
            "clickable": True,
        }
        self.assertTrue(self.selector.is_interactive(input_elem))
        action = self.selector.select_action("screen_1", [input_elem], self.memory)
        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.example.app:id/input_search")
        self.assertIn("semantic_role=text_input", action.reason)

    def test_switch_checkbox_radio_explorable(self) -> None:
        """Test D: Switch, checkbox, and radio controls remain fully explorable."""
        elements = [
            {
                "element_id": "switch_notif",
                "type": "android.widget.Switch",
                "text": "Notifications",
                "clickable": True,
            },
            {
                "element_id": "cb_agree",
                "type": "android.widget.CheckBox",
                "text": "Agree",
                "clickable": True,
            },
            {
                "element_id": "rb_opt1",
                "type": "android.widget.RadioButton",
                "text": "Option 1",
                "clickable": True,
            },
        ]

        explored_ids = []
        for _ in range(3):
            action = self.selector.select_action("screen_prefs", elements, self.memory)
            el_id = action.target.element_id
            explored_ids.append(el_id)
            self.memory.record_attempt("screen_prefs", action.action, el_id)

        # All 3 controls must have been explored
        self.assertEqual(len(explored_ids), 3)
        self.assertIn("switch_notif", explored_ids)
        self.assertIn("cb_agree", explored_ids)
        self.assertIn("rb_opt1", explored_ids)

        # 4th query must return back
        exhausted = self.selector.select_action("screen_prefs", elements, self.memory)
        self.assertEqual(exhausted.action, "back")

    def test_system_ui_elements_remain_rejected(self) -> None:
        """Test E: System UI overlays remain rejected."""
        elements = [
            {
                "element_id": "com.android.systemui:id/scrim_behind",
                "type": "android.view.View",
                "clickable": True,
            },
            {
                "element_id": "android:id/statusBarBackground",
                "type": "android.view.View",
                "clickable": True,
            },
            {
                "element_id": "com.example.app:id/btn_ok",
                "type": "android.widget.Button",
                "text": "OK",
                "clickable": True,
            },
        ]
        action = self.selector.select_action("screen_1", elements, self.memory)
        self.assertEqual(action.target.element_id, "com.example.app:id/btn_ok")

    def test_already_attempted_elements_excluded(self) -> None:
        """Test F: Already attempted elements remain excluded."""
        elements = [
            {
                "element_id": "btn_1",
                "type": "android.widget.Button",
                "text": "First",
                "clickable": True,
            },
            {
                "element_id": "btn_2",
                "type": "android.widget.Button",
                "text": "Second",
                "clickable": True,
            },
        ]
        self.memory.record_attempt("screen_1", "tap", "btn_1")
        action = self.selector.select_action("screen_1", elements, self.memory)
        self.assertEqual(action.target.element_id, "btn_2")

    def test_multiple_meaningful_controls_explored_systematically(self) -> None:
        """Test G: Multiple meaningful controls are explored systematically rather than only one."""
        agent = ExplorationAgent()
        screen = {
            "screen_id": "multi_screen",
            "elements": [
                {"element_id": "btn_search", "type": "android.widget.Button", "text": "Search", "clickable": True},
                {"element_id": "btn_filter", "type": "android.widget.Button", "text": "Filter", "clickable": True},
                {"element_id": "btn_profile", "type": "android.widget.Button", "text": "Profile", "clickable": True},
            ],
        }

        act1 = agent.step(screen)
        act2 = agent.step(screen)
        act3 = agent.step(screen)
        act4 = agent.step(screen)

        chosen = [
            act1["target"]["element_id"],
            act2["target"]["element_id"],
            act3["target"]["element_id"],
        ]
        # Verify 3 distinct controls explored
        self.assertEqual(len(set(chosen)), 3)
        self.assertIn("btn_search", chosen)
        self.assertIn("btn_filter", chosen)
        self.assertIn("btn_profile", chosen)

        # 4th action returns back
        self.assertEqual(act4["action"], "back")

    def test_unknown_elements_do_not_outrank_semantic_controls(self) -> None:
        """Test H: Unknown elements do not outrank meaningful semantic controls."""
        button = {
            "element_id": "btn_checkout",
            "type": "android.widget.Button",
            "text": "Checkout",
            "clickable": True,
        }
        unknown_clickable = {
            "element_id": "elem_frame_99",
            "type": "android.widget.FrameLayout",
            "clickable": True,
        }

        score_button = ActionSelector.compute_element_priority(button)
        score_unknown = ActionSelector.compute_element_priority(unknown_clickable)
        self.assertGreater(score_button, score_unknown)

    def test_selector_phase1_behavior_compatibility(self) -> None:
        """Test I: Existing selector methods and types remain compatible."""
        self.assertTrue(self.selector.is_system_element("com.android.systemui:id/scrim_behind"))
        self.assertFalse(self.selector.is_system_element("com.example.app:id/btn_home"))

        # Disabled element is not interactive
        self.assertFalse(self.selector.is_interactive({"element_id": "d1", "enabled": False, "clickable": True}))

    def test_agent_compatibility_with_semantic_reasons(self) -> None:
        """Test J: Existing Agent tests remain passing and reason is present on tap actions."""
        agent = ExplorationAgent()
        screen = {
            "screen_id": "test_scr",
            "elements": [
                {
                    "element_id": "com.example.app:id/btn_login",
                    "type": "android.widget.Button",
                    "text": "Sign In",
                    "clickable": True,
                }
            ],
        }
        action = agent.step(screen)
        self.assertEqual(action["action"], "tap")
        self.assertEqual(action["target"]["element_id"], "com.example.app:id/btn_login")
        self.assertIn("reason", action)
        self.assertIn("semantic_role=button", action["reason"])

        # Second step exhausted -> back without reason breaking API
        back_action = agent.step(screen)
        self.assertEqual(back_action, {"action": "back"})


if __name__ == "__main__":
    unittest.main()
