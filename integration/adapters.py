"""
Adapters for converting between module-specific representations and the API contract.

Handles bidirectional translation between:
- Android Controller state <-> API Contract ScreenState
- Agent decision <-> API Contract Action
- Controller execution outcome <-> API Contract ActionResult
"""

from typing import Any, Dict, List, Optional


def to_api_screen_state(controller_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an Android Controller state dictionary into the standardized
    ScreenState schema defined in API_CONTRACT.md.

    :param controller_state: Raw state dictionary from Android Controller.
    :return: Standardized ScreenState dictionary conforming to API_CONTRACT.md.
    """
    if not isinstance(controller_state, dict):
        raise TypeError(f"controller_state must be a dict, got {type(controller_state)}")

    screenshot_path = str(controller_state.get("screenshot_path", "") or "")
    current_activity = str(controller_state.get("current_activity", "") or "")
    raw_elements = controller_state.get("elements", []) or []

    normalized_elements: List[Dict[str, Any]] = []
    for elem in raw_elements:
        if not isinstance(elem, dict):
            continue

        bounds = elem.get("bounds", [0, 0, 0, 0])
        if not isinstance(bounds, list) or len(bounds) != 4:
            bounds = [0, 0, 0, 0]
        else:
            bounds = [int(b) for b in bounds]

        center = elem.get("center")
        if not center and bounds != [0, 0, 0, 0]:
            center = [(bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2]
        elif isinstance(center, list) and len(center) == 2:
            center = [int(c) for c in center]
        else:
            center = [(bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2]


        normalized_elements.append({
            "element_id": str(elem.get("element_id", "")),
            "type": str(elem.get("type", "android.view.View")),
            "text": str(elem.get("text", "") or ""),
            "content_description": str(elem.get("content_description", "") or ""),
            "bounds": bounds,
            "center": center,
            "clickable": bool(elem.get("clickable", False)),
            "scrollable": bool(elem.get("scrollable", False)),
            "focusable": bool(elem.get("focusable", False)),
            "enabled": bool(elem.get("enabled", True)),
        })

    return {
        "screenshot_path": screenshot_path,
        "current_activity": current_activity,
        "elements": normalized_elements,
    }


def to_api_action(agent_action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an Agent action dictionary into the standardized Action
    schema defined in API_CONTRACT.md.

    :param agent_action: Raw decision dictionary from ExplorationAgent.
    :return: Standardized Action dictionary conforming to API_CONTRACT.md.
    """
    if not isinstance(agent_action, dict):
        raise TypeError(f"agent_action must be a dict, got {type(agent_action)}")

    action_name = str(agent_action.get("action", "")).lower().strip()
    result: Dict[str, Any] = {"action": action_name}

    target = agent_action.get("target")
    if isinstance(target, dict) and target:
        cleaned_target: Dict[str, Any] = {}
        if "element_id" in target and target["element_id"]:
            cleaned_target["element_id"] = str(target["element_id"])
        if "coordinates" in target:
            cleaned_target["coordinates"] = list(target["coordinates"])
        if cleaned_target:
            result["target"] = cleaned_target

    parameters = agent_action.get("parameters")
    if isinstance(parameters, dict) and parameters:
        result["parameters"] = dict(parameters)

    return result


def to_controller_action(api_action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate an API Contract Action dictionary into the format expected
    by the existing Android Controller execute_action().

    :param api_action: Standardized Action dictionary.
    :return: Controller-compatible action dictionary.
    """
    action_dict = dict(api_action)
    action_type = action_dict.get("action", "").lower()
    parameters = action_dict.get("parameters", {})

    # Map parameters.text to action["text"] for Controller type action
    if action_type == "type" and "text" in parameters and "text" not in action_dict:
        action_dict["text"] = parameters["text"]

    # Map parameters.direction to action["direction"] for Controller scroll action
    if action_type == "scroll" and "direction" in parameters and "direction" not in action_dict:
        action_dict["direction"] = parameters["direction"]

    # Map parameters.duration_ms to action["duration"] in seconds for Controller wait action
    if action_type == "wait":
        if "duration_ms" in parameters and "duration" not in action_dict:
            action_dict["duration"] = parameters["duration_ms"] / 1000.0
        elif "duration" in parameters and "duration" not in action_dict:
            action_dict["duration"] = parameters["duration"]

    return action_dict


def build_action_result(
    success: bool,
    action: Dict[str, Any],
    new_state: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construct an ActionResult dictionary matching Section 3 of API_CONTRACT.md.

    :param success: Boolean indicating if action executed successfully.
    :param action: The action dictionary that was executed.
    :param new_state: The resulting screen state (raw or normalized).
    :param error: Error message if failed; otherwise None.
    :return: Standardized ActionResult dictionary.
    """
    target = action.get("target") or {}
    action_executed = {
        "action": action.get("action", ""),
    }
    if "element_id" in target:
        action_executed["element_id"] = target["element_id"]

    if new_state is not None:
        state_dict = to_api_screen_state(new_state)
    else:
        state_dict = {
            "screenshot_path": "",
            "current_activity": "",
            "elements": [],
        }

    return {
        "success": bool(success),
        "action_executed": action_executed,
        "state": state_dict,
        "error": error if not success else None,
    }
