"""
Unit tests for KnowledgeBuilder and App Knowledge Pack data models.
"""

import json
import os
import sys
import tempfile
import unittest

# Ensure knowledge directory is in sys.path
KNOWLEDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if KNOWLEDGE_DIR not in sys.path:
    sys.path.insert(0, KNOWLEDGE_DIR)

from builder import KnowledgeBuilder
from models import (
    ActionData,
    AppKnowledgePack,
    NavigationGraphData,
    NavigationGraphEdge,
    NavigationGraphNode,
    ScreenData,
    TransitionData,
    UIElementData,
)


class TestKnowledgePackModels(unittest.TestCase):
    """Test suite for Knowledge Pack models and serialization."""

    def test_ui_element_creation_and_dict(self) -> None:
        elem = UIElementData(
            element_id="btn_submit",
            type="android.widget.Button",
            text="Submit",
            content_description="Submit form",
            bounds=[100, 200, 300, 400],
            center=[200, 300],
            clickable=True,
            scrollable=False,
            focusable=True,
            enabled=True,
            purpose="Submits form",
        )
        d = elem.to_dict()
        self.assertEqual(d["element_id"], "btn_submit")
        self.assertEqual(d["center"], [200, 300])

        restored = UIElementData.from_dict(d)
        self.assertEqual(restored.element_id, "btn_submit")
        self.assertEqual(restored.text, "Submit")
        self.assertTrue(restored.clickable)

    def test_screen_data_creation_and_dict(self) -> None:
        screen = ScreenData(
            screen_id="screen_test",
            name="Test Screen",
            purpose="Testing models",
            activity_name="com.test/.TestActivity",
            screenshot_path="path/to/screen.png",
            elements=[
                UIElementData(element_id="e1", type="TextView", text="Hello")
            ],
            actions=[
                ActionData(action_id="a1", action_type="tap", target_element_id="e1")
            ],
            design={"theme": "dark"},
        )
        d = screen.to_dict()
        self.assertEqual(d["screen_id"], "screen_test")
        self.assertEqual(len(d["elements"]), 1)
        self.assertEqual(len(d["actions"]), 1)

        restored = ScreenData.from_dict(d)
        self.assertEqual(restored.name, "Test Screen")
        self.assertEqual(len(restored.elements), 1)
        self.assertEqual(restored.elements[0].element_id, "e1")

    def test_transition_creation_and_dict(self) -> None:
        action = ActionData(action_id="a1", action_type="tap", target_element_id="btn_next")
        trans = TransitionData(
            transition_id="t1",
            source_screen_id="s1",
            action=action,
            destination_screen_id="s2",
            status="success",
        )
        d = trans.to_dict()
        self.assertEqual(d["transition_id"], "t1")
        self.assertEqual(d["action"]["action_type"], "tap")

        restored = TransitionData.from_dict(d)
        self.assertEqual(restored.destination_screen_id, "s2")
        self.assertEqual(restored.action.target_element_id, "btn_next")


class TestKnowledgeBuilder(unittest.TestCase):
    """Test suite for KnowledgeBuilder operations."""

    def setUp(self) -> None:
        self.builder = KnowledgeBuilder(app_name="TestApp", package_name="com.test.app")

    def test_add_and_get_screen(self) -> None:
        screen = ScreenData(
            screen_id="screen_001",
            name="Home",
            purpose="Main screen",
            activity_name="com.test/.MainActivity",
        )
        self.builder.add_screen(screen)
        retrieved = self.builder.get_screen("screen_001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Home")
        self.assertEqual(len(self.builder.list_screens()), 1)

    def test_update_screen(self) -> None:
        self.builder.add_screen({"screen_id": "screen_001", "name": "Initial Name"})
        updated = self.builder.update_screen("screen_001", {"name": "Updated Name", "purpose": "New Purpose"})
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.purpose, "New Purpose")

    def test_add_element_and_action(self) -> None:
        self.builder.add_screen({"screen_id": "screen_001", "name": "Login"})
        elem = self.builder.add_element("screen_001", {
            "element_id": "btn_login",
            "type": "android.widget.Button",
            "text": "Sign In",
            "clickable": True,
        })
        self.assertEqual(elem.element_id, "btn_login")

        act = self.builder.add_action("screen_001", {
            "action_id": "act_login",
            "action_type": "tap",
            "target_element_id": "btn_login",
        })
        self.assertEqual(act.action_id, "act_login")

        screen = self.builder.get_screen("screen_001")
        self.assertEqual(len(screen.elements), 1)
        self.assertEqual(len(screen.actions), 1)

    def test_duplicate_screen_handling(self) -> None:
        # Add initial screen
        self.builder.add_screen(ScreenData(
            screen_id="screen_001",
            name="Home v1",
            elements=[UIElementData(element_id="elem_1", type="TextView", text="Item 1")],
            actions=[ActionData(action_id="act_1", action_type="tap")],
        ))

        # Add duplicate screen with updated title and additional element
        self.builder.add_screen(ScreenData(
            screen_id="screen_001",
            name="Home v2",
            elements=[
                UIElementData(element_id="elem_1", type="TextView", text="Item 1 (Updated)"),
                UIElementData(element_id="elem_2", type="Button", text="Item 2"),
            ],
            actions=[ActionData(action_id="act_2", action_type="scroll")],
        ))

        screen = self.builder.get_screen("screen_001")
        # Should merge without duplicating total screens
        self.assertEqual(len(self.builder.list_screens()), 1)
        self.assertEqual(screen.name, "Home v2")
        self.assertEqual(len(screen.elements), 2)
        self.assertEqual(len(screen.actions), 2)

    def test_record_transition_and_navigation_graph(self) -> None:
        self.builder.add_screen({"screen_id": "s1", "name": "Screen 1"})
        self.builder.add_screen({"screen_id": "s2", "name": "Screen 2"})

        self.builder.record_transition({
            "transition_id": "t1",
            "source_screen_id": "s1",
            "destination_screen_id": "s2",
            "action": {"action_id": "a1", "action_type": "tap", "target_element_id": "btn_next"},
        })

        self.assertEqual(len(self.builder.get_transitions()), 1)
        graph = self.builder.pack.navigation_graph
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].source, "s1")
        self.assertEqual(graph.edges[0].target, "s2")

    def test_graph_validation(self) -> None:
        self.builder.add_screen({"screen_id": "s1", "name": "Screen 1"})
        self.builder.add_screen({"screen_id": "s2", "name": "Screen 2"})

        # Valid transition
        self.builder.record_transition({
            "transition_id": "t1",
            "source_screen_id": "s1",
            "destination_screen_id": "s2",
            "action": {"action_id": "a1", "action_type": "tap"},
        })
        errors = self.builder.validate_graph()
        self.assertEqual(errors, [])

        # Invalid transition referencing non-existent screen
        self.builder.record_transition({
            "transition_id": "t_broken",
            "source_screen_id": "s1",
            "destination_screen_id": "s_ghost",
            "action": {"action_id": "a2", "action_type": "tap"},
        }, update_graph=False)
        errors = self.builder.validate_graph()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("unknown destination screen" in err for err in errors))

    def test_reconstruction_data_generation(self) -> None:
        self.builder.add_screen({
            "screen_id": "screen_rec",
            "name": "Reconstructed Profile",
            "purpose": "Test reconstruction",
            "elements": [
                {
                    "element_id": "title",
                    "type": "android.widget.TextView",
                    "text": "My Profile",
                    "bounds": [0, 0, 1080, 100],
                },
                {
                    "element_id": "btn_save",
                    "type": "android.widget.Button",
                    "text": "Save Changes",
                    "bounds": [100, 200, 980, 320],
                    "clickable": True,
                },
            ],
            "design": {"theme": "dark"},
        })

        rec = self.builder.generate_reconstruction_data("screen_rec")
        self.assertEqual(rec["screen_id"], "screen_rec")
        self.assertEqual(len(rec["components"]), 2)
        self.assertEqual(rec["components"][0]["component_type"], "text")
        self.assertEqual(rec["components"][1]["component_type"], "button")

    def test_export_and_load_json(self) -> None:
        self.builder.add_screen({"screen_id": "s1", "name": "Home"})
        self.builder.add_screen({"screen_id": "s2", "name": "Search"})
        self.builder.record_transition({
            "transition_id": "t1",
            "source_screen_id": "s1",
            "destination_screen_id": "s2",
            "action": {"action_id": "a1", "action_type": "tap"},
        })

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            self.builder.export_json(temp_path)
            loaded_builder = KnowledgeBuilder.load_json(temp_path)
            self.assertEqual(loaded_builder.pack.app_name, "TestApp")
            self.assertEqual(len(loaded_builder.list_screens()), 2)
            self.assertEqual(len(loaded_builder.get_transitions()), 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_sample_knowledge_pack_json_integrity(self) -> None:
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "sample_knowledge_pack.json"
        )
        self.assertTrue(os.path.exists(sample_path))

        loaded_builder = KnowledgeBuilder.load_json(sample_path)
        self.assertEqual(loaded_builder.pack.app_name, "ZeroShop Mobile")
        self.assertEqual(len(loaded_builder.list_screens()), 5)
        self.assertEqual(len(loaded_builder.get_transitions()), 6)

        # Validate graph integrity of sample pack
        validation_errors = loaded_builder.validate_graph()
        self.assertEqual(validation_errors, [])

    def test_navigation_graph_transitions_serialization(self) -> None:
        """Confirm transitions are accessible on navigation_graph and serialized in to_dict."""
        self.builder.add_screen({"screen_id": "s1", "name": "Screen 1"})
        self.builder.add_screen({"screen_id": "s2", "name": "Screen 2"})
        self.builder.record_transition({
            "transition_id": "t1",
            "source_screen_id": "s1",
            "destination_screen_id": "s2",
            "action": {"action_id": "a1", "action_type": "tap"},
            "status": "success",
        })

        graph = self.builder.pack.navigation_graph
        # Property access
        self.assertEqual(len(graph.transitions), 1)
        self.assertEqual(graph.transitions[0].source, "s1")
        self.assertEqual(graph.transitions[0].target, "s2")

        # Serialized dict access
        g_dict = graph.to_dict()
        self.assertIn("transitions", g_dict)
        self.assertIn("edges", g_dict)
        self.assertEqual(len(g_dict["transitions"]), 1)
        self.assertEqual(g_dict["transitions"][0]["source"], "s1")

    def test_duplicate_element_ids_with_different_bounds_not_collapsed(self) -> None:
        """Separate elements sharing element_id (e.g. android:id/title) are preserved."""
        elem1 = UIElementData(
            element_id="android:id/title",
            type="android.widget.TextView",
            text="Network & internet",
            bounds=[0, 100, 500, 200],
            purpose="role=text; label=Network & internet; interaction=none",
        )
        elem2 = UIElementData(
            element_id="android:id/title",
            type="android.widget.TextView",
            text="Connected devices",
            bounds=[0, 200, 500, 300],
            purpose="role=text; label=Connected devices; interaction=none",
        )
        screen = ScreenData(
            screen_id="s1",
            name="Settings",
            elements=[elem1, elem2],
        )
        self.builder.add_screen(screen)
        retrieved = self.builder.get_screen("s1")
        self.assertEqual(len(retrieved.elements), 2)
        self.assertEqual(retrieved.elements[0].text, "Network & internet")
        self.assertEqual(retrieved.elements[1].text, "Connected devices")

    def test_validate_knowledge_pack_integrity(self) -> None:
        """Test validate_knowledge_pack detects both semantic mismatches and broken transitions."""
        from builder import validate_knowledge_pack

        # Valid setup
        self.builder.add_screen({
            "screen_id": "s1",
            "name": "Screen 1",
            "elements": [
                {
                    "element_id": "e1",
                    "text": "Network & internet",
                    "purpose": "role=text; label=Network & internet; interaction=none",
                },
                {
                    "element_id": "e2",
                    "text": "",
                    "content_description": "Search icon",
                    "purpose": "role=button; label=Search icon; interaction=tap",
                },
            ],
        })
        self.builder.add_screen({"screen_id": "s2", "name": "Screen 2"})
        self.builder.record_transition({
            "transition_id": "t1",
            "source_screen_id": "s1",
            "destination_screen_id": "s2",
            "action": {"action_id": "a1", "action_type": "tap"},
            "status": "success",
        })

        res = self.builder.validate_semantic_integrity()
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["element_errors"]), 0)
        self.assertEqual(len(res["transition_errors"]), 0)

        # Introduce semantic mismatch: e1 has text "Network & internet" but label "Sound & vibration"
        self.builder.pack.screens["s1"].elements[0].purpose = "role=text; label=Sound & vibration; interaction=none"
        res2 = self.builder.validate_semantic_integrity()
        self.assertFalse(res2["valid"])
        self.assertEqual(len(res2["element_errors"]), 1)
        self.assertIn("semantic mismatch", res2["element_errors"][0])

        # Restore e1 and break transition
        self.builder.pack.screens["s1"].elements[0].purpose = "role=text; label=Network & internet; interaction=none"
        self.builder.pack.transitions[0].destination_screen_id = "missing_screen"
        res3 = self.builder.validate_semantic_integrity()
        self.assertFalse(res3["valid"])
        self.assertEqual(len(res3["transition_errors"]), 1)
        self.assertIn("missing destination screen", res3["transition_errors"][0])


if __name__ == "__main__":
    unittest.main()
