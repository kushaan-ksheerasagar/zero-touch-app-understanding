"""
Knowledge Builder module.

Provides the KnowledgeBuilder class to construct, update, validate,
and serialize App Knowledge Packs and navigation graphs.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Union

try:
    from .models import (
        ActionData,
        AppKnowledgePack,
        NavigationGraphData,
        NavigationGraphEdge,
        NavigationGraphNode,
        ScreenData,
        TransitionData,
        UIElementData,
    )
except (ImportError, ValueError):
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


class KnowledgeBuilder:
    """Builder and manager for an App Knowledge Pack."""

    def __init__(
        self,
        app_name: str = "Demo App",
        package_name: str = "com.example.app",
        pack: Optional[AppKnowledgePack] = None,
    ) -> None:
        """Initialize KnowledgeBuilder with an existing or new AppKnowledgePack."""
        if pack:
            self.pack = pack
        else:
            self.pack = AppKnowledgePack(
                app_name=app_name,
                package_name=package_name,
            )

    def add_screen(
        self,
        screen: Union[ScreenData, Dict[str, Any]],
        update_graph: bool = True,
    ) -> ScreenData:
        """
        Add or update a screen in the Knowledge Pack.
        If a screen with the same screen_id already exists, updates its fields.
        """
        if isinstance(screen, dict):
            screen_obj = ScreenData.from_dict(screen)
        else:
            screen_obj = screen

        screen_id = screen_obj.screen_id
        if not screen_id:
            raise ValueError("Screen must have a valid non-empty screen_id.")

        if screen_id in self.pack.screens:
            # Handle duplicate screen gracefully: merge elements and update metadata
            existing = self.pack.screens[screen_id]
            existing.name = screen_obj.name or existing.name
            existing.purpose = screen_obj.purpose or existing.purpose
            existing.activity_name = screen_obj.activity_name or existing.activity_name
            existing.screenshot_path = screen_obj.screenshot_path or existing.screenshot_path
            existing.design.update(screen_obj.design)

            # Merge UI elements by element_id
            existing_elem_map = {e.element_id: e for e in existing.elements}
            for new_elem in screen_obj.elements:
                existing_elem_map[new_elem.element_id] = new_elem
            existing.elements = list(existing_elem_map.values())

            # Merge actions by action_id
            existing_act_map = {a.action_id: a for a in existing.actions}
            for new_act in screen_obj.actions:
                existing_act_map[new_act.action_id] = new_act
            existing.actions = list(existing_act_map.values())

            final_screen = existing
        else:
            self.pack.screens[screen_id] = screen_obj
            final_screen = screen_obj

        self.pack.updated_at = time.time()
        if update_graph:
            self.rebuild_navigation_graph()

        return final_screen

    def update_screen(self, screen_id: str, updates: Dict[str, Any]) -> ScreenData:
        """Update specific fields of an existing screen."""
        if screen_id not in self.pack.screens:
            raise KeyError(f"Screen '{screen_id}' does not exist in Knowledge Pack.")

        screen = self.pack.screens[screen_id]
        if "name" in updates:
            screen.name = updates["name"]
        if "purpose" in updates:
            screen.purpose = updates["purpose"]
        if "activity_name" in updates:
            screen.activity_name = updates["activity_name"]
        if "screenshot_path" in updates:
            screen.screenshot_path = updates["screenshot_path"]
        if "design" in updates and isinstance(updates["design"], dict):
            screen.design.update(updates["design"])

        self.pack.updated_at = time.time()
        self.rebuild_navigation_graph()
        return screen

    def add_element(
        self,
        screen_id: str,
        element: Union[UIElementData, Dict[str, Any]],
    ) -> UIElementData:
        """Add a UI element to an existing screen."""
        if screen_id not in self.pack.screens:
            raise KeyError(f"Screen '{screen_id}' does not exist in Knowledge Pack.")

        if isinstance(element, dict):
            elem_obj = UIElementData.from_dict(element)
        else:
            elem_obj = element

        screen = self.pack.screens[screen_id]
        # Replace if element_id exists, else append
        for i, existing in enumerate(screen.elements):
            if existing.element_id == elem_obj.element_id:
                screen.elements[i] = elem_obj
                self.pack.updated_at = time.time()
                return elem_obj

        screen.elements.append(elem_obj)
        self.pack.updated_at = time.time()
        return elem_obj

    def add_action(
        self,
        screen_id: str,
        action: Union[ActionData, Dict[str, Any]],
    ) -> ActionData:
        """Add an action to an existing screen."""
        if screen_id not in self.pack.screens:
            raise KeyError(f"Screen '{screen_id}' does not exist in Knowledge Pack.")

        if isinstance(action, dict):
            act_obj = ActionData.from_dict(action)
        else:
            act_obj = action

        screen = self.pack.screens[screen_id]
        for i, existing in enumerate(screen.actions):
            if existing.action_id == act_obj.action_id:
                screen.actions[i] = act_obj
                self.pack.updated_at = time.time()
                return act_obj

        screen.actions.append(act_obj)
        self.pack.updated_at = time.time()
        return act_obj

    def record_transition(
        self,
        transition: Union[TransitionData, Dict[str, Any]],
        update_graph: bool = True,
    ) -> TransitionData:
        """Record a navigation transition between two screens."""
        if isinstance(transition, dict):
            trans_obj = TransitionData.from_dict(transition)
        else:
            trans_obj = transition

        if not trans_obj.transition_id:
            trans_obj.transition_id = f"trans_{len(self.pack.transitions) + 1:03d}"

        # Prevent exact duplicate transitions
        for i, existing in enumerate(self.pack.transitions):
            if existing.transition_id == trans_obj.transition_id:
                self.pack.transitions[i] = trans_obj
                if update_graph:
                    self.rebuild_navigation_graph()
                return trans_obj

        self.pack.transitions.append(trans_obj)
        self.pack.updated_at = time.time()

        if update_graph:
            self.rebuild_navigation_graph()

        return trans_obj

    def get_screen(self, screen_id: str) -> Optional[ScreenData]:
        """Retrieve screen by screen_id."""
        return self.pack.screens.get(screen_id)

    def list_screens(self) -> List[ScreenData]:
        """List all screens in Knowledge Pack."""
        return list(self.pack.screens.values())

    def get_transitions(self) -> List[TransitionData]:
        """Retrieve all recorded transitions."""
        return list(self.pack.transitions)

    def validate_graph(self) -> List[str]:
        """
        Validate navigation graph references and integrity.
        Returns a list of error/warning strings (empty if completely valid).
        """
        errors = []
        screen_ids = set(self.pack.screens.keys())

        for trans in self.pack.transitions:
            if trans.source_screen_id not in screen_ids:
                errors.append(
                    f"Transition '{trans.transition_id}' references unknown source screen: '{trans.source_screen_id}'"
                )
            if trans.destination_screen_id not in screen_ids:
                errors.append(
                    f"Transition '{trans.transition_id}' references unknown destination screen: '{trans.destination_screen_id}'"
                )

        # Check for isolated/orphan screens (except if only 1 screen exists)
        if len(screen_ids) > 1:
            connected = set()
            for trans in self.pack.transitions:
                connected.add(trans.source_screen_id)
                connected.add(trans.destination_screen_id)
            for sid in screen_ids:
                if sid not in connected:
                    errors.append(f"Screen '{sid}' is isolated with no incoming or outgoing transitions.")

        return errors

    def rebuild_navigation_graph(self) -> NavigationGraphData:
        """Reconstruct NavigationGraph nodes and edges from current screens and transitions."""
        nodes: List[NavigationGraphNode] = []
        is_first = True

        for screen_id, screen in self.pack.screens.items():
            nodes.append(
                NavigationGraphNode(
                    id=screen_id,
                    label=screen.name,
                    activity=screen.activity_name,
                    element_count=len(screen.elements),
                    is_root=is_first,
                )
            )
            is_first = False

        edges: List[NavigationGraphEdge] = []
        for trans in self.pack.transitions:
            action_desc = trans.action.description or trans.action.action_type
            if trans.action.target_element_id:
                action_desc = f"{trans.action.action_type}: {trans.action.target_element_id}"
            edges.append(
                NavigationGraphEdge(
                    id=trans.transition_id,
                    source=trans.source_screen_id,
                    target=trans.destination_screen_id,
                    label=action_desc,
                    action_type=trans.action.action_type,
                )
            )

        graph = NavigationGraphData(nodes=nodes, edges=edges)
        self.pack.navigation_graph = graph
        return graph

    def generate_reconstruction_data(self, screen_id: str) -> Dict[str, Any]:
        """
        Generate structured component reconstruction tree for a screen
        using only data stored in the Knowledge Pack.
        """
        screen = self.get_screen(screen_id)
        if not screen:
            raise KeyError(f"Screen '{screen_id}' not found.")

        components = []
        for elem in screen.elements:
            elem_type = elem.type.split(".")[-1]
            bounds = elem.bounds
            width = bounds[2] - bounds[0] if len(bounds) == 4 else 0
            height = bounds[3] - bounds[1] if len(bounds) == 4 else 0

            # Normalize to web component types
            if "Button" in elem_type:
                comp_type = "button"
            elif "EditText" in elem_type:
                comp_type = "input"
            elif "TextView" in elem_type:
                comp_type = "text"
            elif "Image" in elem_type:
                comp_type = "image"
            elif "RecyclerView" in elem_type or "ListView" in elem_type:
                comp_type = "list"
            elif "BottomNav" in elem_type or "Navigation" in elem_type:
                comp_type = "navbar"
            else:
                comp_type = "container"

            components.append({
                "element_id": elem.element_id,
                "component_type": comp_type,
                "raw_type": elem.type,
                "text": elem.text,
                "content_description": elem.content_description,
                "bounds": bounds,
                "width": width,
                "height": height,
                "clickable": elem.clickable,
                "purpose": elem.purpose,
            })

        return {
            "screen_id": screen.screen_id,
            "name": screen.name,
            "purpose": screen.purpose,
            "design": screen.design,
            "components": components,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert the entire Knowledge Pack to a JSON-serializable dictionary."""
        return self.pack.to_dict()

    def export_json(self, file_path: str, indent: int = 2) -> str:
        """Export the Knowledge Pack to a JSON file."""
        abs_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        data = self.to_dict()
        with open(abs_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
        return abs_path

    @classmethod
    def load_json(cls, file_path: str) -> "KnowledgeBuilder":
        """Load an AppKnowledgePack from a JSON file into a KnowledgeBuilder."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pack = AppKnowledgePack.from_dict(data)
        return cls(pack=pack)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeBuilder":
        """Instantiate KnowledgeBuilder from a dictionary."""
        pack = AppKnowledgePack.from_dict(data)
        return cls(pack=pack)
