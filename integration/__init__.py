"""
Phase 2 Integration module.

Bridges the Android Controller, Exploration Agent, and Knowledge Builder
using standardized API contracts and data models.
"""

try:
    from .adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from .explorer import AutonomousExplorer
    from .fingerprint import compute_screen_fingerprint
    from .knowledge_integration import build_knowledge_builder, build_knowledge_pack
    from .runner import ExplorationResult, IntegrationRunner
except (ImportError, ValueError):
    from adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from explorer import AutonomousExplorer
    from fingerprint import compute_screen_fingerprint
    from knowledge_integration import build_knowledge_builder, build_knowledge_pack
    from runner import ExplorationResult, IntegrationRunner

__all__ = [
    "AutonomousExplorer",
    "IntegrationRunner",
    "ExplorationResult",
    "compute_screen_fingerprint",
    "build_knowledge_pack",
    "build_knowledge_builder",
    "to_api_screen_state",
    "to_api_action",
    "to_controller_action",
    "build_action_result",
]
