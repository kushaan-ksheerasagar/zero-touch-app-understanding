"""
Knowledge Integration module.

Converts an ExplorationResult from IntegrationRunner into a standardized
AppKnowledgePack using the existing KnowledgeBuilder and knowledge data models.

Flow:
    ExplorationResult
          ↓
    KnowledgeBuilder
          ↓
    AppKnowledgePack
          ↓
    JSON export
"""

import os
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from knowledge.builder import KnowledgeBuilder
    from knowledge.models import (
        ActionData,
        AppKnowledgePack,
        ScreenData,
        TransitionData,
        UIElementData,
    )
except (ImportError, ValueError):
    from ..knowledge.builder import KnowledgeBuilder
    from ..knowledge.models import (
        ActionData,
        AppKnowledgePack,
        ScreenData,
        TransitionData,
        UIElementData,
    )


def build_knowledge_builder(
    exploration_result: Any,
    app_metadata: Optional[Dict[str, Any]] = None,
) -> KnowledgeBuilder:
    """
    Constructs and populates a KnowledgeBuilder instance from an ExplorationResult.

    :param exploration_result: ExplorationResult dataclass or dictionary.
    :param app_metadata: Optional dictionary with app_name, package_name, version, etc.
    :return: Populated KnowledgeBuilder instance.
    """
    # 1. Normalize input result access (dataclass or dict)
    if isinstance(exploration_result, dict):
        discovered_states: Dict[str, Dict[str, Any]] = exploration_result.get("discovered_states", {})
        transitions: List[Dict[str, Any]] = exploration_result.get("transitions", [])
        termination_reason: str = exploration_result.get("termination_reason", "completed")
    else:
        discovered_states = getattr(exploration_result, "discovered_states", {})
        transitions = getattr(exploration_result, "transitions", [])
        termination_reason = getattr(exploration_result, "termination_reason", "completed")

    # 2. Extract and infer app metadata
    metadata = dict(app_metadata or {})
    package_name = metadata.pop("package_name", None)
    app_name = metadata.pop("app_name", None)
    version = metadata.pop("version", "1.0")

    # Infer package/app name from discovered states if omitted
    if not package_name or not app_name:
        for state in discovered_states.values():
            if not isinstance(state, dict):
                continue
            activity = str(state.get("current_activity", "") or "")
            if "/" in activity:
                pkg, comp = activity.split("/", 1)
                if not package_name:
                    package_name = pkg.strip()
                if not app_name:
                    app_name = comp.lstrip(".").split(".")[-1] or pkg
                break
            elif activity:
                if not package_name:
                    package_name = activity.split(".")[0]
                if not app_name:
                    app_name = activity
                break

    package_name = package_name or "com.example.app"
    app_name = app_name or "Explored App"

    # 3. Instantiate existing KnowledgeBuilder
    builder = KnowledgeBuilder(app_name=app_name, package_name=package_name)
    builder.pack.version = version
    builder.pack.metadata.update(metadata)
    builder.pack.metadata["termination_reason"] = termination_reason

    # 4. Ingest discovered screens
    for fingerprint, state_data in discovered_states.items():
        if not isinstance(state_data, dict):
            continue

        activity_name = str(state_data.get("current_activity", "") or "")
        screenshot_path = str(state_data.get("screenshot_path", "") or "")

        # Use explicit screen name or derive cleanly from activity
        name = state_data.get("name")
        if not name:
            if "/" in activity_name:
                name = activity_name.split("/")[-1].lstrip(".").split(".")[-1]
            elif activity_name:
                name = activity_name.lstrip(".").split(".")[-1]
            else:
                name = f"Screen {fingerprint[:8]}"


        raw_elements = state_data.get("elements", []) or []
        elements: List[UIElementData] = []
        for elem in raw_elements:
            if isinstance(elem, UIElementData):
                elements.append(elem)
            elif isinstance(elem, dict):
                elements.append(UIElementData.from_dict(elem))

        screen = ScreenData(
            screen_id=fingerprint,
            name=name,
            activity_name=activity_name,
            screenshot_path=screenshot_path,
            elements=elements,
        )
        # Add to builder (handles duplicate screens and merging via existing logic)
        builder.add_screen(screen, update_graph=False)

    # 5. Ingest transitions
    for idx, trans in enumerate(transitions, start=1):
        if not isinstance(trans, dict):
            continue

        src_id = str(trans.get("source_state") or trans.get("source_screen_id") or "")
        dst_id = str(trans.get("destination_state") or trans.get("destination_screen_id") or "")
        action_dict = trans.get("action") or {}
        success = bool(trans.get("success", True))
        error = trans.get("error")

        action_type = str(action_dict.get("action") or action_dict.get("action_type") or "tap")
        target = action_dict.get("target") or {}
        target_element_id = target.get("element_id") or action_dict.get("target_element_id")
        parameters = dict(action_dict.get("parameters") or {})
        if error:
            parameters["error"] = str(error)

        desc = f"{action_type} {target_element_id or ''}".strip()
        action_obj = ActionData(
            action_id=f"act_{idx:03d}",
            action_type=action_type,
            target_element_id=target_element_id,
            parameters=parameters,
            description=desc,
        )

        status = "success" if success else "failed"

        # If action failed and destination is not in pack, destination remains source screen
        # to preserve graph integrity without creating ghost screens
        if not success and dst_id not in builder.pack.screens:
            destination_screen_id = src_id
        else:
            destination_screen_id = dst_id or src_id

        trans_obj = TransitionData(
            transition_id=f"trans_{idx:03d}",
            source_screen_id=src_id,
            action=action_obj,
            destination_screen_id=destination_screen_id,
            status=status,
        )
        builder.record_transition(trans_obj, update_graph=False)

    # 6. Rebuild complete navigation graph
    builder.rebuild_navigation_graph()
    return builder


def build_knowledge_pack(
    exploration_result: Any,
    app_metadata: Optional[Dict[str, Any]] = None,
) -> AppKnowledgePack:
    """
    Converts an ExplorationResult into an AppKnowledgePack.

    :param exploration_result: ExplorationResult dataclass or dictionary.
    :param app_metadata: Optional dictionary with app_name, package_name, version, etc.
    :return: Standardized AppKnowledgePack instance.
    """
    builder = build_knowledge_builder(exploration_result, app_metadata)
    return builder.pack
