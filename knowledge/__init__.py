"""
App Knowledge Pack package.

Provides structured models and builder for creating, managing, and exporting
reusable knowledge representations of Android applications.
"""

try:
    from .builder import KnowledgeBuilder
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

__all__ = [
    "AppKnowledgePack",
    "ScreenData",
    "UIElementData",
    "ActionData",
    "TransitionData",
    "NavigationGraphData",
    "NavigationGraphNode",
    "NavigationGraphEdge",
    "KnowledgeBuilder",
]
