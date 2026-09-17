"""
Data models for App Knowledge Pack.

Defines standardized, dataclass-based representations for UI elements, actions,
screens, navigation transitions, graphs, and the complete App Knowledge Pack.
"""

from dataclasses import asdict, dataclass, field
import time
from typing import Any, Dict, List, Optional, Union


@dataclass
class UIElementData:
    """Represents a single UI element on an Android screen."""
    element_id: str
    type: str
    text: str = ""
    content_description: str = ""
    bounds: List[int] = field(default_factory=lambda: [0, 0, 0, 0])  # [x1, y1, x2, y2]
    center: List[int] = field(default_factory=lambda: [0, 0])        # [x, y]
    clickable: bool = False
    scrollable: bool = False
    focusable: bool = False
    enabled: bool = True
    purpose: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UIElementData":
        bounds = data.get("bounds", [0, 0, 0, 0])
        center = data.get("center", [0, 0])
        if not center and bounds and len(bounds) == 4:
            center = [(bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2]

        return cls(
            element_id=data.get("element_id", ""),
            type=data.get("type", "android.view.View"),
            text=data.get("text", ""),
            content_description=data.get("content_description", ""),
            bounds=bounds,
            center=center,
            clickable=bool(data.get("clickable", False)),
            scrollable=bool(data.get("scrollable", False)),
            focusable=bool(data.get("focusable", False)),
            enabled=bool(data.get("enabled", True)),
            purpose=data.get("purpose", ""),
        )


@dataclass
class ActionData:
    """Represents an actionable interaction on a screen or element."""
    action_id: str
    action_type: str  # "tap", "type", "scroll", "back", "wait"
    target_element_id: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionData":
        return cls(
            action_id=data.get("action_id", ""),
            action_type=data.get("action_type", "tap"),
            target_element_id=data.get("target_element_id"),
            parameters=data.get("parameters", {}),
            description=data.get("description", ""),
        )


@dataclass
class TransitionData:
    """Represents a navigation transition from one screen to another."""
    transition_id: str
    source_screen_id: str
    action: ActionData
    destination_screen_id: str
    status: str = "success"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if isinstance(self.action, ActionData):
            result["action"] = self.action.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransitionData":
        action_raw = data.get("action", {})
        action_obj = action_raw if isinstance(action_raw, ActionData) else ActionData.from_dict(action_raw)
        return cls(
            transition_id=data.get("transition_id", ""),
            source_screen_id=data.get("source_screen_id", ""),
            action=action_obj,
            destination_screen_id=data.get("destination_screen_id", ""),
            status=data.get("status", "success"),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class ScreenData:
    """Represents a discovered Android screen."""
    screen_id: str
    name: str
    purpose: str = ""
    activity_name: str = ""
    screenshot_path: str = ""
    elements: List[UIElementData] = field(default_factory=list)
    actions: List[ActionData] = field(default_factory=list)
    design: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "name": self.name,
            "purpose": self.purpose,
            "activity_name": self.activity_name,
            "screenshot_path": self.screenshot_path,
            "elements": [e.to_dict() if isinstance(e, UIElementData) else e for e in self.elements],
            "actions": [a.to_dict() if isinstance(a, ActionData) else a for a in self.actions],
            "design": self.design,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenData":
        elements = [
            e if isinstance(e, UIElementData) else UIElementData.from_dict(e)
            for e in data.get("elements", [])
        ]
        actions = [
            a if isinstance(a, ActionData) else ActionData.from_dict(a)
            for a in data.get("actions", [])
        ]
        return cls(
            screen_id=data.get("screen_id", ""),
            name=data.get("name", "Unknown Screen"),
            purpose=data.get("purpose", ""),
            activity_name=data.get("activity_name", ""),
            screenshot_path=data.get("screenshot_path", ""),
            elements=elements,
            actions=actions,
            design=data.get("design", {}),
        )


@dataclass
class NavigationGraphNode:
    """Node in the navigation graph representing a screen."""
    id: str
    label: str
    activity: str = ""
    element_count: int = 0
    is_root: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NavigationGraphNode":
        return cls(
            id=data.get("id", ""),
            label=data.get("label", ""),
            activity=data.get("activity", ""),
            element_count=int(data.get("element_count", 0)),
            is_root=bool(data.get("is_root", False)),
        )


@dataclass
class NavigationGraphEdge:
    """Directed edge in the navigation graph representing an action transition."""
    id: str
    source: str
    target: str
    label: str = ""
    action_type: str = "tap"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NavigationGraphEdge":
        return cls(
            id=data.get("id", ""),
            source=data.get("source", ""),
            target=data.get("target", ""),
            label=data.get("label", ""),
            action_type=data.get("action_type", "tap"),
        )


@dataclass
class NavigationGraphData:
    """Complete application navigation graph."""
    nodes: List[NavigationGraphNode] = field(default_factory=list)
    edges: List[NavigationGraphEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() if isinstance(n, NavigationGraphNode) else n for n in self.nodes],
            "edges": [e.to_dict() if isinstance(e, NavigationGraphEdge) else e for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NavigationGraphData":
        nodes = [
            n if isinstance(n, NavigationGraphNode) else NavigationGraphNode.from_dict(n)
            for n in data.get("nodes", [])
        ]
        edges = [
            e if isinstance(e, NavigationGraphEdge) else NavigationGraphEdge.from_dict(e)
            for e in data.get("edges", [])
        ]
        return cls(nodes=nodes, edges=edges)


@dataclass
class AppKnowledgePack:
    """The master App Knowledge Pack document."""
    app_name: str
    package_name: str
    version: str = "1.0"
    exploration_status: str = "completed"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    screens: Dict[str, ScreenData] = field(default_factory=dict)
    transitions: List[TransitionData] = field(default_factory=list)
    navigation_graph: NavigationGraphData = field(default_factory=NavigationGraphData)
    design_system: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_name": self.app_name,
            "package_name": self.package_name,
            "version": self.version,
            "exploration_status": self.exploration_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "screens": {k: v.to_dict() if isinstance(v, ScreenData) else v for k, v in self.screens.items()},
            "transitions": [t.to_dict() if isinstance(t, TransitionData) else t for t in self.transitions],
            "navigation_graph": self.navigation_graph.to_dict() if isinstance(self.navigation_graph, NavigationGraphData) else self.navigation_graph,
            "design_system": self.design_system,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppKnowledgePack":
        screens = {
            k: v if isinstance(v, ScreenData) else ScreenData.from_dict(v)
            for k, v in data.get("screens", {}).items()
        }
        transitions = [
            t if isinstance(t, TransitionData) else TransitionData.from_dict(t)
            for t in data.get("transitions", [])
        ]
        nav_graph_raw = data.get("navigation_graph", {})
        nav_graph = nav_graph_raw if isinstance(nav_graph_raw, NavigationGraphData) else NavigationGraphData.from_dict(nav_graph_raw)

        return cls(
            app_name=data.get("app_name", ""),
            package_name=data.get("package_name", ""),
            version=data.get("version", "1.0"),
            exploration_status=data.get("exploration_status", "completed"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            screens=screens,
            transitions=transitions,
            navigation_graph=nav_graph,
            design_system=data.get("design_system", {}),
            metadata=data.get("metadata", {}),
        )
