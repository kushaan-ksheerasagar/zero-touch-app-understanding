"""
Tests for Phase 3.4 Provider-Neutral LLM Reasoner Adapter and Offline Safety Guardrails.

Validates:
- Requirements A through O
- Prompt generation with compact semantic context (no raw XML dumps)
- Strict model output parsing and validation (actions, element existence, enabled state, type/scroll checks)
- Prevention of coordinate invention and hallucinated element IDs
- Safe fallback to 'back' on any model error, timeout, malformed JSON, or safety violation
- Seamless integration with ExplorationAgent(reasoner=LLMReasoner(...))
- Complete offline testability with FakeLLMClient
"""

import json
import unittest
from typing import Any, Dict

from agent.agent import ExplorationAgent
from agent.llm_reasoner import FakeLLMClient, LLMReasoner, build_reasoning_prompt
from agent.memory import ExplorationMemory
from agent.reasoning import ReasoningContext, build_reasoning_context
from agent.safety import SafetyValidator
from agent.semantic import ElementRole, ScreenType
from agent.types import ActionTarget, AgentAction


class TestLLMReasoner(unittest.TestCase):
    """Unit and integration tests for LLMReasoner with FakeLLMClient."""

    def setUp(self) -> None:
        self.context = ReasoningContext(
            screen_id="screen_search",
            screen_type=ScreenType.SETTINGS,
            likely_purpose="Configure application settings and network",
            current_activity="com.example.app.SettingsActivity",
            elements=[
                {
                    "element_id": "com.example:id/search_box",
                    "role": ElementRole.TEXT_INPUT,
                    "label": "Search Settings",
                    "interaction": "type",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "explored": False,
                },
                {
                    "element_id": "com.example:id/btn_wifi",
                    "role": ElementRole.BUTTON,
                    "label": "Wi-Fi Preferences",
                    "interaction": "tap",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "explored": False,
                },
                {
                    "element_id": "com.example:id/btn_disabled_bluetooth",
                    "role": ElementRole.BUTTON,
                    "label": "Bluetooth (Disabled)",
                    "interaction": "tap",
                    "clickable": False,
                    "scrollable": False,
                    "enabled": False,
                    "explored": False,
                },
                {
                    "element_id": "com.example:id/scroll_list",
                    "role": ElementRole.SCROLL_CONTAINER,
                    "label": "",
                    "interaction": "scroll",
                    "clickable": False,
                    "scrollable": True,
                    "enabled": True,
                    "explored": False,
                },
                {
                    "element_id": "com.example:id/btn_delete_cache",
                    "role": ElementRole.BUTTON,
                    "label": "Delete Cache and Reset",
                    "interaction": "tap",
                    "clickable": True,
                    "scrollable": False,
                    "enabled": True,
                    "explored": False,
                },
            ],
            explored_element_ids=[],
            available_interactions=[
                {
                    "element_id": "com.example:id/search_box",
                    "role": ElementRole.TEXT_INPUT,
                    "label": "Search Settings",
                    "interaction": "type",
                },
                {
                    "element_id": "com.example:id/btn_wifi",
                    "role": ElementRole.BUTTON,
                    "label": "Wi-Fi Preferences",
                    "interaction": "tap",
                },
            ],
            recent_actions=[{"action": "tap", "element_id": "com.example:id/home"}],
            recent_screens=["screen_home"],
            exploration_step=2,
        )

    # Requirement A: Valid tap response
    def test_a_valid_tap_response(self) -> None:
        client = FakeLLMClient({
            "action": "tap",
            "target": {"element_id": "com.example:id/btn_wifi"},
            "reason": "Exploring Wi-Fi preferences button",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "tap")
        self.assertIsNotNone(action.target)
        self.assertEqual(action.target.element_id, "com.example:id/btn_wifi")
        self.assertEqual(action.reason, "Exploring Wi-Fi preferences button")

    # Requirement B: Valid back response
    def test_b_valid_back_response(self) -> None:
        client = FakeLLMClient({
            "action": "back",
            "reason": "Returning to main screen because no useful actions remain",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertEqual(
            action.reason,
            "Returning to main screen because no useful actions remain",
        )

    # Requirement C: Valid stop response
    def test_c_valid_stop_response(self) -> None:
        client = FakeLLMClient({
            "action": "stop",
            "reason": "Exploration goal achieved",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "stop")
        self.assertEqual(action.reason, "Exploration goal achieved")

    # Requirement D: Valid type response
    def test_d_valid_type_response(self) -> None:
        client = FakeLLMClient({
            "action": "type",
            "target": {
                "element_id": "com.example:id/search_box",
                "text": "Display settings",
            },
            "reason": "Searching for display preferences",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "type")
        self.assertIsNotNone(action.target)
        self.assertEqual(action.target.element_id, "com.example:id/search_box")
        self.assertEqual(action.target.extra.get("text"), "Display settings")
        self.assertEqual(action.reason, "Searching for display preferences")

    # Requirement E: Invalid JSON returns safe fallback
    def test_e_invalid_json_fallback(self) -> None:
        client = FakeLLMClient("I think we should click the search button here!")
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("malformed JSON", action.reason)

    # Requirement F: Missing action field returns safe fallback
    def test_f_missing_action_field(self) -> None:
        client = FakeLLMClient({
            "target": {"element_id": "com.example:id/btn_wifi"},
            "reason": "Missing action key entirely",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("missing 'action'", action.reason)

    # Requirement G: Unknown action returns safe fallback
    def test_g_unknown_action(self) -> None:
        client = FakeLLMClient({
            "action": "double_tap_and_hold",
            "target": {"element_id": "com.example:id/btn_wifi"},
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("unsupported action", action.reason)

    # Requirement H: Nonexistent element ID (hallucination) returns safe fallback
    def test_h_nonexistent_element_id_rejected(self) -> None:
        client = FakeLLMClient({
            "action": "tap",
            "target": {"element_id": "com.example:id/hallucinated_button"},
            "reason": "Inventing a button not on the screen",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("does not exist", action.reason)

    # Requirement I: Disabled element rejected with safe fallback
    def test_i_disabled_element_rejected(self) -> None:
        client = FakeLLMClient({
            "action": "tap",
            "target": {"element_id": "com.example:id/btn_disabled_bluetooth"},
            "reason": "Attempting to tap disabled control",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("is disabled", action.reason)

    # Requirement J: Destructive action blocked by safety layer
    def test_j_destructive_action_blocked(self) -> None:
        client = FakeLLMClient({
            "action": "tap",
            "target": {"element_id": "com.example:id/btn_delete_cache"},
            "reason": "Deleting cache data",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("safety policy", action.reason)

    # Requirement K: Model exception caught and falls back to back
    def test_k_model_exception_handled(self) -> None:
        client = FakeLLMClient(exception=RuntimeError("Connection refused by provider"))
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("model client error", action.reason)
        self.assertIn("RuntimeError", action.reason)

    # Requirement L: Timeout / failed request handled safely
    def test_l_timeout_handled_safely(self) -> None:
        client = FakeLLMClient(exception=TimeoutError("Request timed out after 30s"))
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("TimeoutError", action.reason)

    # Requirement M: Prompt contains compact semantic context
    def test_m_prompt_contains_compact_semantic_context(self) -> None:
        prompt = build_reasoning_prompt(self.context)

        self.assertIn("SCREEN INFORMATION:", prompt)
        self.assertIn(self.context.screen_id, prompt)
        self.assertIn(self.context.screen_type, prompt)
        self.assertIn(self.context.likely_purpose, prompt)
        self.assertIn(self.context.current_activity, prompt)
        self.assertIn("com.example:id/search_box", prompt)
        self.assertIn("Wi-Fi Preferences", prompt)
        self.assertIn("EXPLORATION INSTRUCTIONS:", prompt)

    # Requirement N: Prompt does NOT contain raw XML / tree data
    def test_n_prompt_excludes_raw_ui_dumps(self) -> None:
        raw_screen_data = {
            "screen_id": "screen_test",
            "current_activity": "com.app.MainActivity",
            "elements": [
                {
                    "element_id": "elem_1",
                    "resource_id": "elem_1",
                    "class_name": "android.widget.Button",
                    "bounds": [10, 20, 300, 400],
                    "raw_xml_tree": "<node class='android.widget.Button'></node>",
                    "clickable": True,
                    "text": "Click Me",
                }
            ],
        }
        context = build_reasoning_context(raw_screen_data)
        prompt = build_reasoning_prompt(context)

        # Ensure verbose coordinate matrices and raw XML dumps are NOT in the prompt
        self.assertNotIn("[10, 20, 300, 400]", prompt)
        self.assertNotIn("raw_xml_tree", prompt)
        self.assertNotIn("<node class=", prompt)

    # Requirement O: AgentAction conversion works correctly
    def test_o_agent_action_conversion(self) -> None:
        client = FakeLLMClient({
            "action": "scroll",
            "target": {"element_id": "com.example:id/scroll_list"},
            "reason": "Scroll downward to reveal more options",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertIsInstance(action, AgentAction)
        action_dict = action.to_dict()
        self.assertEqual(action_dict["action"], "scroll")
        self.assertEqual(
            action_dict["target"]["element_id"],
            "com.example:id/scroll_list",
        )
        self.assertEqual(
            action_dict["reason"],
            "Scroll downward to reveal more options",
        )

    # Requirement: Coordinates cannot be invented by the model
    def test_coordinate_invention_rejected(self) -> None:
        client = FakeLLMClient({
            "action": "tap",
            "target": {"x": 500, "y": 800},
            "reason": "Tapping random coordinates",
        })
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "back")
        self.assertIn("coordinate targets not permitted", action.reason)

    # Requirement: Markdown code fence extraction works
    def test_markdown_code_fence_json_extracted(self) -> None:
        markdown_wrapped = """Here is the next action to take:
```json
{
  "action": "tap",
  "target": {
    "element_id": "com.example:id/btn_wifi"
  },
  "reason": "Entering wifi preferences"
}
```
Hope this helps!"""
        client = FakeLLMClient(markdown_wrapped)
        reasoner = LLMReasoner(client=client)
        action = reasoner.decide(self.context)

        self.assertEqual(action.action, "tap")
        self.assertEqual(action.target.element_id, "com.example:id/btn_wifi")
        self.assertEqual(action.reason, "Entering wifi preferences")

    # Requirement 9: Integration with ExplorationAgent
    def test_exploration_agent_with_llm_reasoner(self) -> None:
        client = FakeLLMClient([
            {
                "action": "tap",
                "target": {"element_id": "com.example:id/btn_wifi"},
                "reason": "Explore wifi settings first",
            },
            {
                "action": "type",
                "target": {
                    "element_id": "com.example:id/search_box",
                    "text": "bluetooth",
                },
                "reason": "Search for bluetooth",
            },
        ])
        reasoner = LLMReasoner(client=client)
        agent = ExplorationAgent(reasoner=reasoner)

        screen_data = {
            "screen_id": "screen_search",
            "current_activity": "com.example.app.SettingsActivity",
            "elements": [
                {
                    "element_id": "com.example:id/btn_wifi",
                    "text": "Wi-Fi Preferences",
                    "clickable": True,
                    "class_name": "android.widget.Button",
                },
                {
                    "element_id": "com.example:id/search_box",
                    "text": "Search",
                    "clickable": True,
                    "class_name": "android.widget.EditText",
                },
            ],
        }

        # Step 1: Injected LLM reasoner returns tap on wifi
        step1 = agent.step(screen_data)
        self.assertEqual(step1["action"], "tap")
        self.assertEqual(step1["target"]["element_id"], "com.example:id/btn_wifi")
        self.assertEqual(step1["reason"], "Explore wifi settings first")

        # Step 2: Injected LLM reasoner returns type in search
        step2 = agent.step(screen_data)
        self.assertEqual(step2["action"], "type")
        self.assertEqual(step2["target"]["element_id"], "com.example:id/search_box")
        self.assertEqual(step2["target"]["text"], "bluetooth")

        # Confirm default ExplorationAgent() still uses deterministic selector without reasoner
        default_agent = ExplorationAgent()
        self.assertIsNone(default_agent.reasoner)
        default_step = default_agent.step(screen_data)
        self.assertIn("action", default_step)
        self.assertEqual(default_step["action"], "tap")


if __name__ == "__main__":
    unittest.main()
