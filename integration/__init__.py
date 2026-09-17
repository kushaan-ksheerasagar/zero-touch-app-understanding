"""
Phase 2 Integration module.

Bridges the Android Controller and Exploration Agent using the standardized API contract.
"""

try:
    from .adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from .runner import IntegrationRunner
except (ImportError, ValueError):
    from adapters import (
        build_action_result,
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from runner import IntegrationRunner

__all__ = [
    "IntegrationRunner",
    "to_api_screen_state",
    "to_api_action",
    "to_controller_action",
    "build_action_result",
]
