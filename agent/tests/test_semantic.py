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

    def test_semantic_consistency_network_and_internet(self) -> None:
        """Regression: text 'Network & internet' must produce label 'Network & internet'."""
        elem = {
            "element_id": "android:id/title",
            "type": "android.widget.TextView",
            "text": "Network & internet",
            "content_description": "",
        }
        res = classify_element(elem)
        self.assertEqual(res["label"], "Network & internet")
        self.assertEqual(res["role"], ElementRole.TEXT)

    def test_semantic_consistency_connected_devices(self) -> None:
        """Regression: text 'Connected devices' must produce label 'Connected devices'."""
        elem = {
            "element_id": "android:id/title",
            "type": "android.widget.TextView",
            "text": "Connected devices",
            "content_description": "",
        }
        res = classify_element(elem)
        self.assertEqual(res["label"], "Connected devices")
        self.assertEqual(res["role"], ElementRole.TEXT)

    def test_empty_text_uses_content_description(self) -> None:
        """Regression: empty text + content_description must use the content description."""
        elem = {
            "element_id": "android:id/icon",
            "type": "android.widget.ImageView",
            "text": "",
            "content_description": "Search settings",
        }
        res = classify_element(elem)
        self.assertEqual(res["label"], "Search settings")

        # When visible text is also present, visible text takes precedence
        elem_with_both = {
            "element_id": "android:id/button",
            "type": "android.widget.Button",
            "text": "Save",
            "content_description": "Save current settings",
            "clickable": True,
        }
        res_both = classify_element(elem_with_both)
        self.assertEqual(res_both["label"], "Save")

    def test_separate_elements_never_share_labels_accidentally(self) -> None:
        """Regression: separate elements with the same element_id must never share labels."""
        raw_elements = [
            {
                "element_id": "android:id/title",
                "type": "android.widget.TextView",
                "text": "Network & internet",
                "content_description": "",
            },
            {
                "element_id": "android:id/title",
                "type": "android.widget.TextView",
                "text": "Connected devices",
                "content_description": "",
            },
            {
                "element_id": "android:id/title",
                "type": "android.widget.TextView",
                "text": "Sound & vibration",
                "content_description": "",
            },
        ]
        screen = {
            "screen_id": "settings_root",
            "elements": raw_elements,
        }
        understanding = analyze_screen(screen)
        labels = [e["label"] for e in understanding.elements]
        self.assertEqual(labels, ["Network & internet", "Connected devices", "Sound & vibration"])
        self.assertEqual(understanding.elements[0]["label"], "Network & internet")
        self.assertEqual(understanding.elements[1]["label"], "Connected devices")
        self.assertEqual(understanding.elements[2]["label"], "Sound & vibration")

    def test_repeated_analysis_does_not_leak_semantic_state(self) -> None:
        """Regression: repeated analysis of different screens must not leak semantic state."""
        screen_1 = {
            "screen_id": "screen_1",
            "elements": [
                {
                    "element_id": "android:id/title",
                    "type": "android.widget.TextView",
                    "text": "Sound & vibration",
                }
            ],
        }
        screen_2 = {
            "screen_id": "screen_2",
            "elements": [
                {
                    "element_id": "android:id/title",
                    "type": "android.widget.TextView",
                    "text": "Network & internet",
                }
            ],
        }

        # Analyze screen 1
        und_1 = analyze_screen(screen_1)
        self.assertEqual(und_1.elements[0]["label"], "Sound & vibration")

        # Analyze screen 2 immediately after
        und_2 = analyze_screen(screen_2)
        self.assertEqual(und_2.elements[0]["label"], "Network & internet")

        # Check raw dicts were not mutated
        self.assertNotIn("role", screen_1["elements"][0])
        self.assertNotIn("role", screen_2["elements"][0])


if __name__ == "__main__":
    unittest.main()
