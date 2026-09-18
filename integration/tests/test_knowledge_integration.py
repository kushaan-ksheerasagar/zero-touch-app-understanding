"""
Unit tests for Knowledge Integration layer (Phase 2.4).

Tests:
A. One discovered state becomes one knowledge screen.
B. UI elements are correctly converted.
C. A transition becomes a Knowledge Pack transition.
D. Multiple transitions are preserved.
E. Duplicate/identical states do not create duplicate Knowledge Pack screens when the existing builder considers them the same.
F. Failed transitions preserve failure information without creating an invalid destination screen.
G. The resulting AppKnowledgePack can be exported to JSON and imported again using the existing functionality.
H. Empty ExplorationResult produces a valid empty Knowledge Pack.
"""

import json
import os
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INTEGRATION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KNOWLEDGE_DIR = os.path.abspath(os.path.join(ROOT_DIR, "knowledge"))

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if INTEGRATION_DIR not in sys.path:
    sys.path.insert(0, INTEGRATION_DIR)
if KNOWLEDGE_DIR not in sys.path:
    sys.path.insert(0, KNOWLEDGE_DIR)

from integration.knowledge_integration import (
    build_knowledge_builder,
    build_knowledge_pack,
)
from integration.runner import ExplorationResult
from knowledge.builder import KnowledgeBuilder
from knowledge.models import (
    AppKnowledgePack,
    ScreenData,
    TransitionData,
    UIElementData,
)


class TestKnowledgeIntegration(unittest.TestCase):
    """Test suite for converting ExplorationResult into AppKnowledgePack."""

    def setUp(self) -> None:
        self.state_home = {
            "current_activity": "com.example.shop/com.example.shop.MainActivity",
            "screenshot_path": "screenshots/home.png",
            "elements": [
                {
                    "element_id": "com.example.shop:id/btn_search",
                    "type": "android.widget.Button",
                    "text": "Search",
                    "content_description": "Search items",
                    "bounds": [100, 100, 400, 200],
                    "center": [250, 150],
                    "clickable": True,
                    "scrollable": False,
                    "focusable": True,
                    "enabled": True,
                },
                {
                    "element_id": "com.example.shop:id/input_code",
                    "type": "android.widget.EditText",
                    "text": "Promo",
                    "content_description": "Enter code",
                    "bounds": [100, 300, 500, 400],
                    "center": [300, 350],
                    "clickable": True,
                    "scrollable": False,
                    "focusable": True,
                    "enabled": True,
                },
            ],
        }

        self.state_search = {
            "current_activity": "com.example.shop/com.example.shop.SearchActivity",
            "screenshot_path": "screenshots/search.png",
            "elements": [
                {
                    "element_id": "com.example.shop:id/query",
                    "type": "android.widget.EditText",
                    "text": "",
                    "content_description": "Query",
                    "bounds": [50, 50, 600, 150],
                    "center": [325, 100],
                    "clickable": True,
                    "scrollable": False,
                    "focusable": True,
                    "enabled": True,
                }
            ],
        }

        self.state_results = {
            "current_activity": "com.example.shop/com.example.shop.ResultsActivity",
            "screenshot_path": "screenshots/results.png",
            "elements": [
                {
                    "element_id": "com.example.shop:id/item_1",
                    "type": "android.widget.TextView",
                    "text": "Product 1",
                    "content_description": "Product Description",
                    "bounds": [50, 200, 800, 300],
                    "center": [425, 250],
                    "clickable": True,
                    "scrollable": False,
                    "focusable": False,
                    "enabled": True,
                }
            ],
        }

    def test_single_discovered_state_becomes_screen(self) -> None:
        """Test A: One discovered state becomes one knowledge screen."""
        result = ExplorationResult(
            discovered_states={"state_home_123": self.state_home},
            transitions=[],
            termination_reason="max_steps_reached",
        )

        pack = build_knowledge_pack(result)

        self.assertIsInstance(pack, AppKnowledgePack)
        self.assertEqual(len(pack.screens), 1)
        self.assertIn("state_home_123", pack.screens)

        screen = pack.screens["state_home_123"]
        self.assertEqual(screen.screen_id, "state_home_123")
        self.assertEqual(screen.activity_name, "com.example.shop/com.example.shop.MainActivity")
        self.assertEqual(screen.screenshot_path, "screenshots/home.png")
        self.assertEqual(screen.name, "MainActivity")
        self.assertEqual(pack.package_name, "com.example.shop")

    def test_ui_elements_conversion(self) -> None:
        """Test B: UI elements are correctly converted into UIElementData."""
        result = ExplorationResult(
            discovered_states={"state_home_123": self.state_home},
            transitions=[],
            termination_reason="max_steps_reached",
        )

        pack = build_knowledge_pack(result)
        screen = pack.screens["state_home_123"]

        self.assertEqual(len(screen.elements), 2)
        e1 = screen.elements[0]
        self.assertIsInstance(e1, UIElementData)
        self.assertEqual(e1.element_id, "com.example.shop:id/btn_search")
        self.assertEqual(e1.type, "android.widget.Button")
        self.assertEqual(e1.text, "Search")
        self.assertEqual(e1.content_description, "Search items")
        self.assertEqual(e1.bounds, [100, 100, 400, 200])
        self.assertEqual(e1.center, [250, 150])
        self.assertTrue(e1.clickable)
        self.assertFalse(e1.scrollable)
        self.assertTrue(e1.focusable)
        self.assertTrue(e1.enabled)

        e2 = screen.elements[1]
        self.assertEqual(e2.element_id, "com.example.shop:id/input_code")
        self.assertEqual(e2.type, "android.widget.EditText")
        self.assertEqual(e2.text, "Promo")

    def test_transition_conversion(self) -> None:
        """Test C: A transition becomes a Knowledge Pack transition."""
        trans = {
            "source_state": "state_home_123",
            "destination_state": "state_search_456",
            "action": {
                "action": "tap",
                "target": {"element_id": "com.example.shop:id/btn_search"},
            },
            "success": True,
            "error": None,
        }
        result = ExplorationResult(
            discovered_states={
                "state_home_123": self.state_home,
                "state_search_456": self.state_search,
            },
            transitions=[trans],
            termination_reason="max_steps_reached",
        )

        pack = build_knowledge_pack(result)

        self.assertEqual(len(pack.transitions), 1)
        t = pack.transitions[0]
        self.assertIsInstance(t, TransitionData)
        self.assertEqual(t.source_screen_id, "state_home_123")
        self.assertEqual(t.destination_screen_id, "state_search_456")
        self.assertEqual(t.status, "success")
        self.assertEqual(t.action.action_type, "tap")
        self.assertEqual(t.action.target_element_id, "com.example.shop:id/btn_search")

        # Verify NavigationGraph was populated
        self.assertEqual(len(pack.navigation_graph.nodes), 2)
        self.assertEqual(len(pack.navigation_graph.edges), 1)
        self.assertEqual(pack.navigation_graph.edges[0].source, "state_home_123")
        self.assertEqual(pack.navigation_graph.edges[0].target, "state_search_456")

    def test_multiple_transitions_preserved(self) -> None:
        """Test D: Multiple transitions are preserved and graph integrity holds."""
        transitions = [
            {
                "source_state": "state_1",
                "destination_state": "state_2",
                "action": {"action": "tap", "target": {"element_id": "btn_1"}},
                "success": True,
            },
            {
                "source_state": "state_2",
                "destination_state": "state_3",
                "action": {"action": "tap", "target": {"element_id": "btn_2"}},
                "success": True,
            },
        ]
        result = ExplorationResult(
            discovered_states={
                "state_1": self.state_home,
                "state_2": self.state_search,
                "state_3": self.state_results,
            },
            transitions=transitions,
            termination_reason="max_steps_reached",
        )

        builder = build_knowledge_builder(result)
        pack = builder.pack

        self.assertEqual(len(pack.screens), 3)
        self.assertEqual(len(pack.transitions), 2)
        self.assertEqual(len(pack.navigation_graph.edges), 2)

        validation_errors = builder.validate_graph()
        self.assertEqual(validation_errors, [])

    def test_duplicate_states_handled_by_existing_builder(self) -> None:
        """Test E: Duplicate/identical states do not create duplicate screens."""
        # Initial builder
        builder = KnowledgeBuilder(app_name="Shop", package_name="com.example.shop")
        # Add state once
        builder.add_screen(ScreenData(
            screen_id="state_same",
            name="Home v1",
            activity_name="MainActivity",
            elements=[UIElementData(element_id="btn_1", type="Button", text="Click")],
        ))

        # Build exploration result with the exact same screen_id but updated info
        updated_state = dict(self.state_home)
        result = ExplorationResult(
            discovered_states={"state_same": updated_state},
            transitions=[],
            termination_reason="max_steps_reached",
        )

        pack = build_knowledge_pack(result)
        # Should contain exactly one screen with merged elements
        self.assertEqual(len(pack.screens), 1)
        self.assertIn("state_same", pack.screens)

    def test_failed_transition_preserves_error_without_invalid_destination(self) -> None:
        """Test F: Failed transitions preserve failure information without creating an invalid destination screen."""
        failed_trans = {
            "source_state": "state_home_123",
            "destination_state": "state_ghost_999",  # Non-existent destination screen
            "action": {
                "action": "tap",
                "target": {"element_id": "btn_broken"},
            },
            "success": False,
            "error": "Target element 'btn_broken' not found",
        }
        result = ExplorationResult(
            discovered_states={"state_home_123": self.state_home},
            transitions=[failed_trans],
            termination_reason="action_failed",
        )

        builder = build_knowledge_builder(result)
        pack = builder.pack

        self.assertEqual(len(pack.transitions), 1)
        t = pack.transitions[0]
        self.assertEqual(t.status, "failed")
        self.assertEqual(t.source_screen_id, "state_home_123")
        # Destination is clamped to source screen so it does not reference a ghost screen
        self.assertEqual(t.destination_screen_id, "state_home_123")
        self.assertEqual(t.action.parameters["error"], "Target element 'btn_broken' not found")

        # Graph validation should pass cleanly without broken references
        errors = builder.validate_graph()
        self.assertEqual(errors, [])

    def test_export_and_reimport_json(self) -> None:
        """Test G: The resulting AppKnowledgePack can be exported to JSON and imported again."""
        trans = {
            "source_state": "state_home_123",
            "destination_state": "state_search_456",
            "action": {"action": "tap", "target": {"element_id": "com.example.shop:id/btn_search"}},
            "success": True,
        }
        result = ExplorationResult(
            discovered_states={
                "state_home_123": self.state_home,
                "state_search_456": self.state_search,
            },
            transitions=[trans],
            termination_reason="max_steps_reached",
        )

        builder = build_knowledge_builder(result, app_metadata={"app_name": "ExportApp", "version": "2.1"})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            builder.export_json(temp_path)
            self.assertTrue(os.path.exists(temp_path))

            # Re-import using existing KnowledgeBuilder.load_json
            loaded_builder = KnowledgeBuilder.load_json(temp_path)
            loaded_pack = loaded_builder.pack

            self.assertEqual(loaded_pack.app_name, "ExportApp")
            self.assertEqual(loaded_pack.version, "2.1")
            self.assertEqual(len(loaded_pack.screens), 2)
            self.assertEqual(len(loaded_pack.transitions), 1)
            self.assertEqual(len(loaded_pack.navigation_graph.nodes), 2)
            self.assertEqual(len(loaded_pack.navigation_graph.edges), 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_empty_exploration_result(self) -> None:
        """Test H: Empty ExplorationResult produces a valid empty Knowledge Pack."""
        empty_result = ExplorationResult(
            steps=[],
            discovered_states={},
            transitions=[],
            termination_reason="max_steps_reached",
        )

        pack = build_knowledge_pack(empty_result)

        self.assertIsInstance(pack, AppKnowledgePack)
        self.assertEqual(len(pack.screens), 0)
        self.assertEqual(len(pack.transitions), 0)
        self.assertEqual(len(pack.navigation_graph.nodes), 0)
        self.assertEqual(len(pack.navigation_graph.edges), 0)

        # Ensure serialize to dict works
        d = pack.to_dict()
        self.assertIn("screens", d)
        self.assertIn("navigation_graph", d)

        # Ensure reload from dict works
        restored = AppKnowledgePack.from_dict(d)
        self.assertEqual(len(restored.screens), 0)


if __name__ == "__main__":
    unittest.main()
