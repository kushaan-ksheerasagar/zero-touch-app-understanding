"""
Tests for Phase 3.3 Reasoning Architecture and Safety Validation.

Validates:
- Compact ReasoningContext construction (excluding raw UI tree dumps)
- Explored element tracking in reasoning context
- BaseReasoner abstraction and RuleBasedReasoner decision heuristics
- Safety validation layer blocking destructive actions
- Integration into ExplorationAgent while preserving backward compatibility
- Offline execution without external APIs or keys
"""

import sys
import unittest
from typing import Any, Dict

from agent.agent import ExplorationAgent
from agent.memory import ExplorationMemory
from agent.reasoning import (
    BaseReasoner,
    ReasoningContext,
    RuleBasedReasoner,
    build_reasoning_context,
)
from agent.safety import DEFAULT_RISKY_PATTERNS, SafetyValidator, validate_action
from agent.semantic import ElementRole, ScreenType, analyze_screen
from agent.types import ActionTarget, AgentAction


class TestReasoningArchitecture(unittest.TestCase):
    """Unit and integration tests for reasoning module, safety layer, and agent integration."""

    def setUp(self) -> None:
        self.sample_screen_data: Dict[str, Any] = {
            "screen_id": "settings_main",
            "current_activity": "com.android.settings.SettingsActivity",
            "elements": [
                {
                    "element_id": "com.android.settings:id/network_settings",
                    "resource_id": "com.android.settings:id/network_settings",
                    "class_name": "android.widget.TextView",
                    "text": "Network & internet",
                    "content_description": "Mobile, Wi-Fi, hotspot",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "bounds": [0, 200, 1080, 360],
                    "raw_hierarchy_depth": 5,
                },
                {
                    "element_id": "com.android.settings:id/display_settings",
                    "resource_id": "com.android.settings:id/display_settings",
                    "class_name": "android.widget.TextView",
                    "text": "Display",
                    "content_description": "Wallpaper, sleep, font size",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "bounds": [0, 360, 1080, 520],
                    "raw_hierarchy_depth": 5,
                },
                {
                    "element_id": "com.android.systemui:id/navigationBarBackground",
                    "resource_id": "com.android.systemui:id/navigationBarBackground",
                    "class_name": "android.view.View",
                    "text": "",
                    "content_description": "",
                    "clickable": False,
                    "scrollable": False,
                    "enabled": True,
                    "bounds": [0, 2200, 1080, 2400],
                    "raw_hierarchy_depth": 2,
                },
            ],
        }

    # Requirement A: ReasoningContext contains compact semantic information
    def test_a_reasoning_context_contains_compact_semantic_info(self) -> None:
        memory = ExplorationMemory()
        context = build_reasoning_context(
            screen_data=self.sample_screen_data,
            memory=memory,
            screen_id="settings_main",
            exploration_step=1,
        )

        self.assertIsInstance(context, ReasoningContext)
        self.assertEqual(context.screen_id, "settings_main")
        self.assertEqual(context.screen_type, ScreenType.SETTINGS)
        self.assertIn("settings", context.likely_purpose.lower())
        self.assertEqual(context.current_activity, "com.android.settings.SettingsActivity")
        self.assertEqual(context.exploration_step, 1)

        # Verify semantic fields on elements
        for elem in context.elements:
            self.assertIn("element_id", elem)
            self.assertIn("role", elem)
            self.assertIn("label", elem)
            self.assertIn("interaction", elem)
            self.assertIn("clickable", elem)
            self.assertIn("scrollable", elem)
            self.assertIn("enabled", elem)
            self.assertIn("explored", elem)

    # Requirement B: Raw irrelevant UI fields are not unnecessarily copied
    def test_b_raw_irrelevant_ui_fields_excluded_from_context(self) -> None:
        context = build_reasoning_context(screen_data=self.sample_screen_data)

        # Check that verbose raw Android UI fields are NOT present in reasoning context elements
        for elem in context.elements:
            self.assertNotIn("bounds", elem)
            self.assertNotIn("raw_hierarchy_depth", elem)
            self.assertNotIn("resource_id", elem)
            self.assertNotIn("class_name", elem)
            self.assertNotIn("parent", elem)
            self.assertNotIn("children", elem)

    # Requirement C: Explored elements are marked correctly
    def test_c_explored_elements_marked_correctly(self) -> None:
        memory = ExplorationMemory()
        explored_id = "com.android.settings:id/network_settings"
        memory.record_attempt(
            screen_id="settings_main",
            action="tap",
            element_id=explored_id,
        )

        context = build_reasoning_context(
            screen_data=self.sample_screen_data,
            memory=memory,
            screen_id="settings_main",
        )

        self.assertIn(explored_id, context.explored_element_ids)

        for elem in context.elements:
            if elem["element_id"] == explored_id:
                self.assertTrue(elem["explored"])
            else:
                self.assertFalse(elem["explored"])

        # Explored element should NOT be listed in available_interactions
        available_ids = [item["element_id"] for item in context.available_interactions]
        self.assertNotIn(explored_id, available_ids)

    # Requirement D: RuleBasedReasoner chooses an unexplored meaningful control
    def test_d_rule_based_reasoner_chooses_unexplored_meaningful_control(self) -> None:
        screen = {
            "screen_id": "home_feed",
            "elements": [
                {
                    "element_id": "com.app:id/generic_container",
                    "class_name": "android.view.ViewGroup",
                    "clickable": True,
                    "text": "",
                    "content_description": "",
                },
                {
                    "element_id": "com.app:id/btn_login",
                    "class_name": "android.widget.Button",
                    "clickable": True,
                    "text": "Sign In",
                    "content_description": "",
                },
            ],
        }
        context = build_reasoning_context(screen_data=screen)
        reasoner = RuleBasedReasoner()
        decision = reasoner.decide(context)

        self.assertEqual(decision.action, "tap")
        self.assertIsNotNone(decision.target)
        self.assertEqual(decision.target.element_id, "com.app:id/btn_login")

    # Requirement E: RuleBasedReasoner can choose navigation
    def test_e_rule_based_reasoner_can_choose_navigation(self) -> None:
        screen = {
            "screen_id": "main_hub",
            "elements": [
                {
                    "element_id": "com.app:id/nav_settings",
                    "class_name": "android.widget.ImageView",
                    "clickable": True,
                    "text": "",
                    "content_description": "Settings Menu Navigation",
                },
                {
                    "element_id": "com.app:id/status_text",
                    "class_name": "android.widget.TextView",
                    "clickable": True,
                    "text": "Status",
                },
            ],
        }
        context = build_reasoning_context(screen_data=screen)
        reasoner = RuleBasedReasoner()
        decision = reasoner.decide(context)

        self.assertEqual(decision.action, "tap")
        self.assertEqual(decision.target.element_id, "com.app:id/nav_settings")

    # Requirement F: RuleBasedReasoner avoids already explored elements
    def test_f_rule_based_reasoner_avoids_already_explored_elements(self) -> None:
        memory = ExplorationMemory()
        first_target = "com.android.settings:id/network_settings"
        memory.record_attempt(
            screen_id="settings_main",
            action="tap",
            element_id=first_target,
        )

        context = build_reasoning_context(
            screen_data=self.sample_screen_data,
            memory=memory,
            screen_id="settings_main",
        )
        reasoner = RuleBasedReasoner()
        decision = reasoner.decide(context)

        self.assertEqual(decision.action, "tap")
        self.assertNotEqual(decision.target.element_id, first_target)
        self.assertEqual(
            decision.target.element_id,
            "com.android.settings:id/display_settings",
        )

    # Requirement G: RuleBasedReasoner avoids system UI
    def test_g_rule_based_reasoner_avoids_system_ui(self) -> None:
        screen = {
            "screen_id": "overlay_screen",
            "elements": [
                {
                    "element_id": "com.android.systemui:id/scrim_behind",
                    "class_name": "android.view.View",
                    "clickable": True,
                },
                {
                    "element_id": "com.app:id/btn_action",
                    "class_name": "android.widget.Button",
                    "clickable": True,
                    "text": "Continue",
                },
            ],
        }
        context = build_reasoning_context(screen_data=screen)
        reasoner = RuleBasedReasoner()
        decision = reasoner.decide(context)

        self.assertEqual(decision.target.element_id, "com.app:id/btn_action")

    # Requirement H: RuleBasedReasoner falls back to back when appropriate
    def test_h_rule_based_reasoner_falls_back_to_back(self) -> None:
        memory = ExplorationMemory()
        # Mark all interactive elements as explored
        for elem in self.sample_screen_data["elements"]:
            el_id = elem.get("element_id")
            if el_id:
                memory.record_attempt(
                    screen_id="settings_main",
                    action="tap",
                    element_id=el_id,
                )

        context = build_reasoning_context(
            screen_data=self.sample_screen_data,
            memory=memory,
            screen_id="settings_main",
        )
        reasoner = RuleBasedReasoner()
        decision = reasoner.decide(context)

        self.assertEqual(decision.action, "back")
        self.assertIn("No unexplored safe interactions", decision.reason)

    # Requirement I: Destructive actions are blocked by the safety layer
    def test_i_destructive_actions_blocked_by_safety(self) -> None:
        validator = SafetyValidator()

        # Test risky words in target element IDs or labels
        risky_cases = [
            {"element_id": "com.app:id/btn_delete_account", "label": "Delete Account"},
            {"element_id": "com.app:id/btn_uninstall", "label": "Uninstall App"},
            {"element_id": "com.app:id/confirm_deletion", "label": "Confirm Deletion"},
            {"element_id": "com.app:id/purchase_item", "label": "Purchase Now"},
            {"element_id": "com.app:id/pay_button", "label": "Pay with card"},
            {"element_id": "com.app:id/transfer_funds", "label": "Transfer money"},
            {"element_id": "com.app:id/factory_reset", "label": "Factory Reset"},
            {"element_id": "com.app:id/send_money", "label": "Send Money"},
            {"element_id": "com.app:id/submit_form", "label": "Submit"},
        ]

        for case in risky_cases:
            action = AgentAction(
                action="tap",
                target=ActionTarget(element_id=case["element_id"]),
            )
            mock_context = ReasoningContext(
                screen_id="danger_screen",
                screen_type="unknown",
                likely_purpose="",
                current_activity="",
                elements=[case],
            )
            result = validator.validate_action(action, mock_context)
            self.assertFalse(
                result.allowed,
                f"Expected destructive action {case} to be blocked by safety validator",
            )
            self.assertIsNotNone(result.reason)

    # Requirement J: Safe actions are allowed
    def test_j_safe_actions_are_allowed(self) -> None:
        validator = SafetyValidator()
        safe_action = AgentAction(
            action="tap",
            target=ActionTarget(element_id="com.app:id/btn_view_profile"),
        )
        safe_context = ReasoningContext(
            screen_id="profile_screen",
            screen_type="profile",
            likely_purpose="View profile",
            current_activity="",
            elements=[{"element_id": "com.app:id/btn_view_profile", "label": "View Profile"}],
        )
        result = validator.validate_action(safe_action, safe_context)
        self.assertTrue(result.allowed)
        self.assertIsNone(result.reason)

        # Back and Wait are always safe
        self.assertTrue(validator.validate_action(AgentAction(action="back")).allowed)
        self.assertTrue(validator.validate_action(AgentAction(action="wait")).allowed)

    # Requirement K: Reason field is populated
    def test_k_reason_field_is_populated(self) -> None:
        context = build_reasoning_context(screen_data=self.sample_screen_data)
        reasoner = RuleBasedReasoner()
        decision = reasoner.decide(context)

        self.assertIsNotNone(decision.reason)
        self.assertTrue(len(decision.reason) > 0)
        self.assertIn("semantic_role", decision.reason)

        # Verify reason in to_dict()
        action_dict = decision.to_dict()
        self.assertIn("reason", action_dict)
        self.assertEqual(action_dict["reason"], decision.reason)

    # Requirement L: Existing ExplorationAgent() behavior remains compatible
    def test_l_existing_exploration_agent_behavior_compatible(self) -> None:
        # Instantiating with no arguments must default to selector logic without breaking
        agent = ExplorationAgent()
        self.assertIsNone(agent.reasoner)

        action_dict = agent.step(self.sample_screen_data)
        self.assertIn("action", action_dict)
        self.assertEqual(action_dict["action"], "tap")
        self.assertIn("target", action_dict)
        self.assertIn("element_id", action_dict["target"])

        # Subsequent step avoids already explored element
        second_action = agent.step(self.sample_screen_data)
        self.assertNotEqual(
            action_dict["target"]["element_id"],
            second_action["target"]["element_id"],
        )

    # Requirement M: Injected reasoner is actually used when provided
    def test_m_injected_reasoner_is_used(self) -> None:
        class SpyReasoner(BaseReasoner):
            def __init__(self) -> None:
                self.invoked = False
                self.last_received_context = None

            def decide(self, context: ReasoningContext) -> AgentAction:
                self.invoked = True
                self.last_received_context = context
                return AgentAction(
                    action="tap",
                    target=ActionTarget(element_id="com.mock:id/custom_choice"),
                    reason="custom spy reasoner decision",
                )

        spy = SpyReasoner()
        agent = ExplorationAgent(reasoner=spy)

        action_dict = agent.step(self.sample_screen_data)

        self.assertTrue(spy.invoked)
        self.assertIsNotNone(spy.last_received_context)
        self.assertEqual(spy.last_received_context.screen_id, "settings_main")
        self.assertEqual(action_dict["target"]["element_id"], "com.mock:id/custom_choice")
        self.assertEqual(action_dict["reason"], "custom spy reasoner decision")
        self.assertEqual(agent.get_current_context(), spy.last_received_context)

    # Requirement N: No network/API dependency is required
    def test_n_no_network_or_api_dependency(self) -> None:
        # Confirm no external AI packages are loaded
        for forbidden_module in (
            "openai",
            "anthropic",
            "google.generativeai",
            "google.ai.generativelanguage",
            "requests",
            "urllib3",
        ):
            self.assertNotIn(
                forbidden_module,
                sys.modules,
                f"Forbidden network/API module '{forbidden_module}' found in sys.modules",
            )

    # Requirement 9: Full Integration Test
    def test_full_pipeline_offline_integration(self) -> None:
        """
        Demonstrates the complete Phase 3.3 offline reasoning pipeline:
        ScreenState -> semantic understanding -> ReasoningContext -> RuleBasedReasoner -> safety validation -> AgentAction
        """
        dangerous_screen = {
            "screen_id": "account_management",
            "current_activity": "com.app.account.ManageActivity",
            "elements": [
                {
                    "element_id": "com.app:id/btn_delete_account",
                    "class_name": "android.widget.Button",
                    "clickable": True,
                    "text": "Delete Account",
                    "bounds": [0, 0, 100, 50],
                },
                {
                    "element_id": "com.app:id/btn_view_details",
                    "class_name": "android.widget.Button",
                    "clickable": True,
                    "text": "View Details",
                    "bounds": [0, 60, 100, 110],
                },
            ],
        }

        # 1. Pipeline with RuleBasedReasoner and SafetyValidator
        safety = SafetyValidator()
        reasoner = RuleBasedReasoner(safety_validator=safety)
        agent = ExplorationAgent(reasoner=reasoner, safety_validator=safety)

        # Step 1: Reasoner should avoid "Delete Account" and select "View Details"
        action1 = agent.step(dangerous_screen)
        self.assertEqual(action1["action"], "tap")
        self.assertEqual(action1["target"]["element_id"], "com.app:id/btn_view_details")
        self.assertIn("reason", action1)

        # Step 2: Now "View Details" is explored. Remaining element is destructive.
        # Reasoner/Safety should prevent executing "Delete Account" and fall back safely.
        action2 = agent.step(dangerous_screen)
        self.assertEqual(action2["action"], "back")
        self.assertIn("safe", action2["reason"].lower())


if __name__ == "__main__":
    unittest.main()
