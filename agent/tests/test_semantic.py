"""
Unit tests for deterministic semantic screen understanding (Phase 3.1).

Tests:
A. Button classification
B. Text input classification
C. Switch classification
D. Checkbox classification
E. Scroll container classification
F. Label extraction from text/content_description
G. Login screen detection
H. Settings screen detection
I. Unknown screen when evidence is insufficient
J. Existing Agent behavior remains compatible
"""

import os
import sys
import unittest

# Ensure project root is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.agent import ExplorationAgent
from agent.semantic import (
    ElementRole,
    ScreenType,
    ScreenUnderstanding,
    analyze_screen,
    classify_element,
    extract_label,
)


class TestSemanticUnderstanding(unittest.TestCase):
    """Test suite for semantic element and screen classification."""

    def test_button_classification(self) -> None:
        """Test A: Button classification."""
        btn_elem = {
            "element_id": "btn_submit",
            "type": "android.widget.Button",
            "text": "Submit",
            "clickable": True,
        }
        res = classify_element(btn_elem)
        self.assertEqual(res["role"], ElementRole.BUTTON)
        self.assertEqual(res["interaction"], "tap")
        self.assertEqual(res["label"], "Submit")
        # Ensure original fields remain preserved
        self.assertEqual(res["type"], "android.widget.Button")
        self.assertTrue(res["clickable"])

        # ImageButton
        img_btn = {
            "element_id": "btn_back",
            "type": "android.widget.ImageButton",
            "content_description": "Navigate back",
            "clickable": True,
        }
        res2 = classify_element(img_btn)
        self.assertEqual(res2["role"], ElementRole.BUTTON)
        self.assertEqual(res2["interaction"], "tap")
        self.assertEqual(res2["label"], "Navigate back")

    def test_text_input_classification(self) -> None:
        """Test B: Text input classification."""
        input_elem = {
            "element_id": "input_email",
            "type": "android.widget.EditText",
            "text": "",
            "content_description": "Enter email address",
            "focusable": True,
        }
        res = classify_element(input_elem)
        self.assertEqual(res["role"], ElementRole.TEXT_INPUT)
        self.assertEqual(res["interaction"], "type")
        self.assertEqual(res["label"], "Enter email address")

        material_input = {
            "element_id": "input_query",
            "type": "com.google.android.material.textfield.TextInputEditText",
            "text": "Query",
        }
        res2 = classify_element(material_input)
        self.assertEqual(res2["role"], ElementRole.TEXT_INPUT)
        self.assertEqual(res2["interaction"], "type")

    def test_switch_classification(self) -> None:
        """Test C: Switch classification."""
        switch_elem = {
            "element_id": "switch_wifi",
            "type": "android.widget.Switch",
            "text": "Wi-Fi",
            "clickable": True,
        }
        res = classify_element(switch_elem)
        self.assertEqual(res["role"], ElementRole.SWITCH)
        self.assertEqual(res["interaction"], "tap")
        self.assertEqual(res["label"], "Wi-Fi")

        compat_switch = {
            "element_id": "switch_dark",
            "type": "androidx.appcompat.widget.SwitchCompat",
            "text": "Dark Mode",
        }
        res2 = classify_element(compat_switch)
        self.assertEqual(res2["role"], ElementRole.SWITCH)
        self.assertEqual(res2["interaction"], "tap")

    def test_checkbox_classification(self) -> None:
        """Test D: Checkbox classification."""
        cb_elem = {
            "element_id": "cb_terms",
            "type": "android.widget.CheckBox",
            "text": "I agree to Terms & Conditions",
            "clickable": True,
        }
        res = classify_element(cb_elem)
        self.assertEqual(res["role"], ElementRole.CHECKBOX)
        self.assertEqual(res["interaction"], "tap")
        self.assertEqual(res["label"], "I agree to Terms & Conditions")

    def test_scroll_container_classification(self) -> None:
        """Test E: Scroll container classification."""
        recycler = {
            "element_id": "recycler_feed",
            "type": "androidx.recyclerview.widget.RecyclerView",
            "scrollable": True,
        }
        res = classify_element(recycler)
        self.assertEqual(res["role"], ElementRole.SCROLL_CONTAINER)
        self.assertEqual(res["interaction"], "scroll")

        scrollview = {
            "element_id": "scroll_view",
            "type": "android.widget.ScrollView",
            "scrollable": False,  # classified by type
        }
        res2 = classify_element(scrollview)
        self.assertEqual(res2["role"], ElementRole.SCROLL_CONTAINER)
        self.assertEqual(res2["interaction"], "scroll")

    def test_label_extraction(self) -> None:
        """Test F: Label extraction from text and content_description."""
        # Case 1: Visible text available
        e1 = {"text": "Search Products", "content_description": ""}
        self.assertEqual(extract_label(e1), "Search Products")

        # Case 2: Only content_description available
        e2 = {"text": "", "content_description": "Microphone voice input"}
        self.assertEqual(extract_label(e2), "Microphone voice input")

        # Case 3: Both available (prefers visible text)
        e3 = {"text": "Visible Label", "content_description": "Accessibility Label"}
        self.assertEqual(extract_label(e3), "Visible Label")

        # Case 4: Neither available
        e4 = {"text": "", "content_description": ""}
        self.assertEqual(extract_label(e4), "")

    def test_login_screen_detection(self) -> None:
        """Test G: Login screen detection."""
        screen = {
            "screen_id": "login_screen",
            "current_activity": "com.example.app/.LoginActivity",
            "elements": [
                {
                    "element_id": "input_user",
                    "type": "android.widget.EditText",
                    "text": "",
                    "content_description": "Username",
                },
                {
                    "element_id": "input_password",
                    "type": "android.widget.EditText",
                    "text": "",
                    "content_description": "Password",
                },
                {
                    "element_id": "btn_login",
                    "type": "android.widget.Button",
                    "text": "Sign In",
                    "clickable": True,
                },
            ],
        }
        understanding = analyze_screen(screen)
        self.assertEqual(understanding.screen_type, ScreenType.LOGIN)
        self.assertIn("authentication", understanding.likely_purpose.lower())
        self.assertGreaterEqual(len(understanding.important_elements), 2)
        important_ids = [e["element_id"] for e in understanding.important_elements]
        self.assertIn("input_password", important_ids)
        self.assertIn("btn_login", important_ids)

    def test_settings_screen_detection(self) -> None:
        """Test H: Settings screen detection."""
        screen = {
            "screen_id": "settings_screen",
            "current_activity": "com.android.settings/.Settings",
            "elements": [
                {
                    "element_id": "switch_wifi",
                    "type": "android.widget.Switch",
                    "text": "Wi-Fi",
                    "clickable": True,
                },
                {
                    "element_id": "switch_bluetooth",
                    "type": "android.widget.Switch",
                    "text": "Bluetooth",
                    "clickable": True,
                },
                {
                    "element_id": "item_display",
                    "type": "android.widget.TextView",
                    "text": "Display and Brightness",
                    "clickable": True,
                },
            ],
        }
        understanding = analyze_screen(screen)
        self.assertEqual(understanding.screen_type, ScreenType.SETTINGS)
        self.assertIn("settings", understanding.likely_purpose.lower())
        self.assertGreaterEqual(len(understanding.important_elements), 2)

    def test_unknown_screen_when_insufficient_evidence(self) -> None:
        """Test I: Unknown screen when evidence is insufficient."""
        screen = {
            "screen_id": "unknown_screen",
            "current_activity": "com.example.app/.GenericActivity",
            "elements": [
                {
                    "element_id": "container_box",
                    "type": "android.widget.FrameLayout",
                },
                {
                    "element_id": "image_banner",
                    "type": "android.widget.ImageView",
                    "content_description": "",
                },
            ],
        }
        understanding = analyze_screen(screen)
        self.assertEqual(understanding.screen_type, ScreenType.UNKNOWN)
        self.assertEqual(understanding.likely_purpose, "")

    def test_existing_agent_behavior_compatibility(self) -> None:
        """Test J: Existing Agent behavior remains completely compatible."""
        agent = ExplorationAgent()
        screen = {
            "screen_id": "search_screen",
            "current_activity": "com.example.shop/.SearchActivity",
            "elements": [
                {
                    "element_id": "input_search",
                    "type": "android.widget.EditText",
                    "text": "",
                    "content_description": "Search products",
                    "clickable": True,
                    "bounds": [50, 50, 600, 150],
                    "center": [325, 100],
                },
                {
                    "element_id": "btn_search",
                    "type": "android.widget.Button",
                    "text": "Search",
                    "clickable": True,
                    "bounds": [620, 50, 750, 150],
                    "center": [685, 100],
                },
            ],
        }

        # Step 1: Agent decides action
        action = agent.step(screen)
        self.assertIn("action", action)
        self.assertIn("target", action)

        # Semantic understanding is populated
        understanding = agent.get_current_understanding()
        self.assertIsNotNone(understanding)
        self.assertIsInstance(understanding, ScreenUnderstanding)
        self.assertEqual(understanding.screen_type, ScreenType.SEARCH)
        self.assertIn("search", understanding.likely_purpose.lower())

        # Original elements are preserved with enriched semantic metadata
        self.assertEqual(len(understanding.elements), 2)
        e0 = understanding.elements[0]
        self.assertEqual(e0["element_id"], "input_search")
        self.assertEqual(e0["role"], ElementRole.TEXT_INPUT)
        self.assertEqual(e0["label"], "Search products")
        self.assertEqual(e0["bounds"], [50, 50, 600, 150])

        # Step 2: Next step avoids repeating element
        action2 = agent.step(screen)
        self.assertNotEqual(
            action.get("target", {}).get("element_id"),
            action2.get("target", {}).get("element_id"),
        )


if __name__ == "__main__":
    unittest.main()
