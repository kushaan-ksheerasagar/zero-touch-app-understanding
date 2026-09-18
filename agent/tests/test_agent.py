import json
import unittest
from agent import ExplorationAgent, ExplorationMemory, ActionSelector


class TestExplorationAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ExplorationAgent()

        self.home_screen = {
            "screen_id": "home",
            "elements": [
                {
                    "element_id": "search_button",
                    "type": "button",
                    "text": "Search",
                    "clickable": True,
                },
                {
                    "element_id": "profile_button",
                    "type": "button",
                    "text": "Profile",
                    "clickable": True,
                },
            ],
        }

    def test_first_action_selection(self):
        action = self.agent.step(self.home_screen)
        self.assertEqual(action["action"], "tap")
        self.assertEqual(action.get("target", {}).get("element_id"), "search_button")

    def test_subsequent_action_selection_avoids_repeated_element(self):
        # First step: selects search_button
        action1 = self.agent.step(self.home_screen)
        self.assertEqual(action1["action"], "tap")
        self.assertEqual(action1["target"]["element_id"], "search_button")

        # Second step on same screen: selects profile_button
        action2 = self.agent.step(self.home_screen)
        self.assertEqual(action2["action"], "tap")
        self.assertEqual(action2["target"]["element_id"], "profile_button")

    def test_back_when_all_elements_explored(self):
        # Exhaust both buttons
        self.agent.step(self.home_screen)
        self.agent.step(self.home_screen)

        # Third step on same screen: should return back
        action3 = self.agent.step(self.home_screen)
        self.assertEqual(action3, {"action": "back"})

    def test_accepts_json_string_input(self):
        json_input = json.dumps(self.home_screen)
        action = self.agent.step(json_input)
        self.assertEqual(action["action"], "tap")
        self.assertEqual(action["target"]["element_id"], "search_button")

    def test_skips_non_interactive_elements(self):
        screen_with_labels = {
            "screen_id": "info_screen",
            "elements": [
                {
                    "element_id": "title_label",
                    "type": "text_view",
                    "text": "Welcome",
                    "clickable": False,
                },
                {
                    "element_id": "submit_btn",
                    "type": "button",
                    "text": "Submit",
                    "clickable": True,
                },
            ],
        }
        action = self.agent.step(screen_with_labels)
        self.assertEqual(action["action"], "tap")
        self.assertEqual(action["target"]["element_id"], "submit_btn")

    def test_screen_without_interactive_elements_returns_back(self):
        static_screen = {
            "screen_id": "static_screen",
            "elements": [
                {
                    "element_id": "static_text",
                    "type": "text_view",
                    "text": "Just reading here",
                    "clickable": False,
                }
            ],
        }
        action = self.agent.step(static_screen)
        self.assertEqual(action, {"action": "back"})

    def test_tracks_different_screens_independently(self):
        search_screen = {
            "screen_id": "search_screen",
            "elements": [
                {
                    "element_id": "search_input",
                    "type": "input",
                    "text": "",
                    "clickable": True,
                }
            ],
        }

        # Step on home
        home_action = self.agent.step(self.home_screen)
        self.assertEqual(home_action["target"]["element_id"], "search_button")

        # Step on search screen
        search_action = self.agent.step(search_screen)
        self.assertEqual(search_action["target"]["element_id"], "search_input")

        # Step on home again: should select profile_button
        home_action_2 = self.agent.step(self.home_screen)
        self.assertEqual(home_action_2["target"]["element_id"], "profile_button")

    def test_memory_clear(self):
        self.agent.step(self.home_screen)
        self.agent.reset()
        # After reset, search_button should be selected again
        action = self.agent.step(self.home_screen)
        self.assertEqual(action["target"]["element_id"], "search_button")

    def test_rejects_system_ui_scrim(self):
        """Test A: System UI scrim and system overlays are rejected."""
        screen_with_scrim = {
            "screen_id": "settings_screen",
            "elements": [
                {
                    "element_id": "com.android.systemui:id/scrim_behind",
                    "type": "android.view.View",
                    "text": "",
                    "clickable": True,
                },
                {
                    "element_id": "android:id/statusBarBackground",
                    "type": "android.view.View",
                    "text": "",
                    "clickable": True,
                },
                {
                    "element_id": "com.android.settings:id/search_action_bar",
                    "type": "android.widget.Button",
                    "text": "Search settings",
                    "clickable": True,
                },
            ],
        }
        action = self.agent.step(screen_with_scrim)
        self.assertEqual(action["action"], "tap")
        self.assertEqual(
            action["target"]["element_id"],
            "com.android.settings:id/search_action_bar"
        )

    def test_prefers_meaningful_control_over_meaningless_clickable(self):
        """Test B: Meaningful application button is preferred over meaningless clickable element."""
        screen_with_mixed_elements = {
            "screen_id": "mixed_screen",
            "elements": [
                # Meaningless clickable container without text or semantic type
                {
                    "element_id": "elem_001_FrameLayout_0_0",
                    "type": "android.widget.FrameLayout",
                    "text": "",
                    "clickable": True,
                },
                # Meaningful button with label and real ID
                {
                    "element_id": "com.example.app:id/btn_checkout",
                    "type": "android.widget.Button",
                    "text": "Checkout Now",
                    "clickable": True,
                },
            ],
        }
        action = self.agent.step(screen_with_mixed_elements)
        self.assertEqual(action["action"], "tap")
        self.assertEqual(
            action["target"]["element_id"],
            "com.example.app:id/btn_checkout"
        )

    def test_only_system_overlays_returns_back(self):
        """Test that a screen with only system overlays navigates back."""
        screen_only_system = {
            "screen_id": "overlay_screen",
            "elements": [
                {
                    "element_id": "com.android.systemui:id/scrim_behind",
                    "type": "android.view.View",
                    "clickable": True,
                },
                {
                    "element_id": "com.android.systemui:id/navigation_bar",
                    "type": "android.view.View",
                    "clickable": True,
                },
            ],
        }
        action = self.agent.step(screen_only_system)
        self.assertEqual(action, {"action": "back"})


if __name__ == "__main__":
    unittest.main()

