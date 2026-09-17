"""
Autonomous Exploration Engine for Android applications.

Coordinates multi-step exploration loop:
OBSERVE -> UNDERSTAND -> DECIDE -> VALIDATE -> ACT -> OBSERVE AGAIN -> REMEMBER -> REPEAT

Integrates:
- AndroidController (device control)
- ExplorationAgent (decision making)
- LLMReasoner / GeminiLLMClient (reasoning)
- SafetyValidator (safety enforcement)
- Screen Fingerprinting (deterministic state tracking)
- KnowledgeBuilder (persistent App Knowledge Pack)
- ExplorationMemory (loop prevention and history)
"""

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from agent.agent import ExplorationAgent
    from agent.memory import ExplorationMemory
    from agent.safety import SafetyValidator
    from agent.semantic import ScreenUnderstanding, analyze_screen
    from agent.types import AgentAction
    from integration.adapters import (
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from integration.fingerprint import compute_screen_fingerprint
    from knowledge.builder import KnowledgeBuilder
    from knowledge.models import ActionData, ScreenData, TransitionData, UIElementData
except (ImportError, ValueError):
    from agent import ExplorationAgent
    from memory import ExplorationMemory
    from safety import SafetyValidator
    from semantic import ScreenUnderstanding, analyze_screen
    from types import AgentAction
    from adapters import (
        to_api_action,
        to_api_screen_state,
        to_controller_action,
    )
    from fingerprint import compute_screen_fingerprint
    from knowledge.builder import KnowledgeBuilder
    from knowledge.models import ActionData, ScreenData, TransitionData, UIElementData


def _serialize_action(action: Dict[str, Any]) -> str:
    """Deterministic string signature of an action for loop detection."""
    action_type = str(action.get("action", "")).lower().strip()
    target = action.get("target") or {}
    el_id = str(target.get("element_id", "") or "").strip()
    coords = target.get("coordinates")
    coords_str = (
        f"{coords[0]},{coords[1]}"
        if isinstance(coords, (list, tuple)) and len(coords) == 2
        else ""
    )
    params = action.get("parameters") or {}
    text = str(params.get("text", "") or "").strip()
    direction = str(params.get("direction", "") or "").strip()
    return f"{action_type}:{el_id}:{coords_str}:{text}:{direction}"


def _get_screen_label(fingerprint: str, screen_state: Dict[str, Any]) -> str:
    """Derives a concise human-readable label for a screen."""
    activity = str(screen_state.get("current_activity", "") or "")
    if "/" in activity:
        comp = activity.split("/")[-1].lstrip(".")
        if "." in comp:
            comp = comp.split(".")[-1]
        return f"{comp} ({fingerprint[:8]})"
    elif activity:
        short = activity.lstrip(".").split(".")[-1]
        return f"{short} ({fingerprint[:8]})"
    return f"Screen_{fingerprint[:8]}"


def _ingest_screen_to_knowledge(
    builder: KnowledgeBuilder,
    screen_id: str,
    screen_state: Dict[str, Any],
    understanding: Optional[ScreenUnderstanding],
) -> None:
    """Adds or updates a discovered screen in KnowledgeBuilder."""
    activity = str(screen_state.get("current_activity", "") or "")
    screenshot_path = str(screen_state.get("screenshot_path", "") or "")
    name = _get_screen_label(screen_id, screen_state)
    purpose = (
        f"{understanding.screen_type}: {understanding.likely_purpose}"
        if understanding
        else "App Screen"
    )

    elements: List[UIElementData] = []
    understanding_elem_map: Dict[str, Dict[str, Any]] = {}
    if understanding and hasattr(understanding, "elements"):
        for ue in understanding.elements:
            if isinstance(ue, dict) and ue.get("element_id"):
                understanding_elem_map[ue["element_id"]] = ue

    for raw_elem in screen_state.get("elements", []):
        el_id = str(raw_elem.get("element_id", ""))
        matched_ue = understanding_elem_map.get(el_id, {})
        role = matched_ue.get("role", "unknown")
        label = matched_ue.get("label", "")
        interaction = matched_ue.get("interaction", "none")

        purpose_str = f"role={role}; label={label}; interaction={interaction}"
        elem_data = UIElementData(
            element_id=el_id,
            type=str(raw_elem.get("type", "android.view.View")),
            text=str(raw_elem.get("text", "") or ""),
            content_description=str(raw_elem.get("content_description", "") or ""),
            bounds=raw_elem.get("bounds", [0, 0, 0, 0]),
            center=raw_elem.get("center", [0, 0]),
            clickable=bool(raw_elem.get("clickable", False)),
            scrollable=bool(raw_elem.get("scrollable", False)),
            focusable=bool(raw_elem.get("focusable", False)),
            enabled=bool(raw_elem.get("enabled", True)),
            purpose=purpose_str,
        )
        elements.append(elem_data)

    screen_data = ScreenData(
        screen_id=screen_id,
        name=name,
        purpose=purpose,
        activity_name=activity,
        screenshot_path=screenshot_path,
        elements=elements,
        design={
            "fingerprint": screen_id,
            "screen_type": understanding.screen_type if understanding else "unknown",
            "likely_purpose": understanding.likely_purpose if understanding else "unknown",
        },
    )
    builder.add_screen(screen_data)


def _ingest_transition_to_knowledge(
    builder: KnowledgeBuilder,
    step_num: int,
    source_id: str,
    action_dict: Dict[str, Any],
    destination_id: str,
    status: str = "success",
    error: Optional[str] = None,
) -> None:
    """Records an executed action transition in KnowledgeBuilder."""
    action_type = str(action_dict.get("action", "tap"))
    target = action_dict.get("target") or {}
    target_el_id = target.get("element_id")
    parameters = dict(action_dict.get("parameters") or {})
    if error:
        parameters["error"] = error

    desc = str(action_dict.get("reason") or f"{action_type} {target_el_id or ''}".strip())

    action_data = ActionData(
        action_id=f"act_{step_num:03d}",
        action_type=action_type,
        target_element_id=target_el_id,
        parameters=parameters,
        description=desc,
    )

    # If action failed and destination screen is not yet known, keep destination as source
    dest_to_record = destination_id if (status == "success" or destination_id in builder.pack.screens) else source_id

    trans_data = TransitionData(
        transition_id=f"trans_{step_num:03d}",
        source_screen_id=source_id,
        action=action_data,
        destination_screen_id=dest_to_record,
        status=status,
    )
    builder.record_transition(trans_data)


class AutonomousExplorer:
    """
    Coordinates bounded autonomous multi-step exploration on Android apps.
    """

    def __init__(
        self,
        controller: Any,
        agent: ExplorationAgent,
        knowledge_builder: Optional[KnowledgeBuilder] = None,
        max_steps: int = 10,
        max_consecutive_backs: int = 3,
        package_name: Optional[str] = None,
        app_name: Optional[str] = None,
        artifacts_path: Optional[str] = None,
        verbose: bool = True,
    ) -> None:
        self.controller = controller
        self.agent = agent
        self.max_steps = max(1, max_steps)
        self.max_consecutive_backs = max(1, max_consecutive_backs)
        self.package_name = package_name or "com.android.app"
        self.app_name = app_name or self.package_name.split(".")[-1].capitalize()
        self.artifacts_path = artifacts_path or os.path.join(PROJECT_ROOT, "artifacts", "app_knowledge_pack.json")
        self.verbose = verbose

        self.knowledge_builder = knowledge_builder or KnowledgeBuilder(
            app_name=self.app_name,
            package_name=self.package_name,
        )

    def run(self) -> Dict[str, Any]:
        """
        Executes the autonomous exploration loop for up to max_steps.
        Returns a dictionary summary conforming to Phase 3.6 specifications.
        """
        steps: List[Dict[str, Any]] = []
        discovered_screens: Dict[str, Dict[str, Any]] = {}
        transitions: List[Dict[str, Any]] = []
        seen_state_actions: Set[Tuple[str, str]] = set()

        consecutive_backs: int = 0
        successful_actions: int = 0
        failed_actions: int = 0
        safety_blocked_actions: int = 0
        termination_reason: str = "max_steps_reached"
        trace: List[Dict[str, Any]] = []

        for step_idx in range(1, self.max_steps + 1):
            # 1. OBSERVE current screen
            raw_state = self.controller.get_current_state()
            screen_state = to_api_screen_state(raw_state)
            current_fp = compute_screen_fingerprint(screen_state)
            screen_state["screen_id"] = current_fp

            # Generate semantic understanding
            understanding = analyze_screen(screen_state)

            # Record screen if newly discovered
            if current_fp not in discovered_screens:
                discovered_screens[current_fp] = screen_state
                _ingest_screen_to_knowledge(
                    self.knowledge_builder, current_fp, screen_state, understanding
                )

            source_label = _get_screen_label(current_fp, screen_state)

            # 2. DECIDE: agent chooses action through LLMReasoner / selector + safety
            raw_agent_action = self.agent.step(screen_state)
            action_name = str(raw_agent_action.get("action", "back")).lower()
            reason = str(raw_agent_action.get("reason", ""))

            # Track safety blocks
            if "safety policy" in reason.lower() or "blocked by safety" in reason.lower():
                safety_blocked_actions += 1

            # 3. LOOP PREVENTION & VALIDATION
            target = raw_agent_action.get("target") or {}
            el_id = target.get("element_id")
            api_action = to_api_action(raw_agent_action)
            action_sig = _serialize_action(api_action)

            # Check if this exact state-action pair was already executed
            if (current_fp, action_sig) in seen_state_actions and action_name not in ("back", "stop"):
                raw_agent_action = {
                    "action": "back",
                    "reason": f"Action '{action_name}' on '{el_id}' already executed on screen; backing out to escape loop",
                }
                api_action = to_api_action(raw_agent_action)
                action_name = "back"

            # Check consecutive BACK presses
            if action_name == "back":
                consecutive_backs += 1
                if consecutive_backs >= self.max_consecutive_backs:
                    termination_reason = "max_consecutive_backs_reached"
                    raw_agent_action = {
                        "action": "stop",
                        "reason": f"Terminal: reached maximum consecutive backs ({self.max_consecutive_backs})",
                    }
                    api_action = to_api_action(raw_agent_action)
                    action_name = "stop"
            else:
                consecutive_backs = 0

            # 4. TERMINAL ACTION CHECK
            if action_name == "stop":
                if termination_reason == "max_steps_reached":
                    termination_reason = "agent_stopped"

                # Record terminal step in trace
                trace.append({
                    "step": step_idx,
                    "source": source_label,
                    "action_desc": "stop",
                    "destination": source_label,
                    "success": True,
                    "screen_changed": False,
                })
                break

            # 5. EXECUTE action through controller
            ctrl_action = to_controller_action(api_action)
            action_succeeded = False
            error_message = None

            try:
                new_raw_state = self.controller.execute_action(ctrl_action)
                action_succeeded = True
                successful_actions += 1
            except Exception as exc:
                action_succeeded = False
                failed_actions += 1
                error_message = str(exc)
                try:
                    new_raw_state = self.controller.get_current_state()
                except Exception:
                    new_raw_state = raw_state

            seen_state_actions.add((current_fp, action_sig))

            # 6. OBSERVE AGAIN & FINGERPRINT
            new_api_state = to_api_screen_state(new_raw_state)
            dest_fp = compute_screen_fingerprint(new_api_state)
            screen_changed = (dest_fp != current_fp)

            if dest_fp not in discovered_screens:
                discovered_screens[dest_fp] = new_api_state
                dest_understanding = analyze_screen(new_api_state)
                _ingest_screen_to_knowledge(
                    self.knowledge_builder, dest_fp, new_api_state, dest_understanding
                )

            dest_label = _get_screen_label(dest_fp, new_api_state)

            # 7. INGEST TRANSITION TO KNOWLEDGEBUILDER
            trans_status = "success" if action_succeeded else "failed"
            _ingest_transition_to_knowledge(
                builder=self.knowledge_builder,
                step_num=step_idx,
                source_id=current_fp,
                action_dict=api_action,
                destination_id=dest_fp,
                status=trans_status,
                error=error_message,
            )

            # 8. RECORD STEP & TRACE
            action_type = api_action.get("action", "")
            action_desc = f"{action_type} {el_id}".strip() if el_id else action_type
            trace_entry = {
                "step": step_idx,
                "source": source_label,
                "action_desc": action_desc,
                "destination": dest_label,
                "success": action_succeeded,
                "screen_changed": screen_changed,
            }
            trace.append(trace_entry)

            step_record = {
                "step_number": step_idx,
                "source_state": current_fp,
                "destination_state": dest_fp,
                "action": api_action,
                "success": action_succeeded,
                "screen_changed": screen_changed,
                "error": error_message,
            }
            steps.append(step_record)
            transitions.append({
                "source_state": current_fp,
                "destination_state": dest_fp,
                "action": api_action,
                "success": action_succeeded,
                "error": error_message,
            })

            # Check if execution failure threshold exceeded
            if failed_actions >= 3:
                termination_reason = "consecutive_action_failures"
                break

        # EXPORT Knowledge Pack
        os.makedirs(os.path.dirname(self.artifacts_path), exist_ok=True)
        self.knowledge_builder.export_json(self.artifacts_path)

        summary = {
            "steps": steps,
            "steps_count": len(steps),
            "discovered_screens_count": len(discovered_screens),
            "unique_screens_count": len(self.knowledge_builder.pack.screens),
            "transitions_count": len(transitions),
            "successful_actions": successful_actions,
            "failed_actions": failed_actions,
            "safety_blocked_actions": safety_blocked_actions,
            "termination_reason": termination_reason,
            "knowledge_pack_path": self.artifacts_path,
            "trace": trace,
        }

        if self.verbose:
            self._print_report(summary)

        return summary

    def _print_report(self, summary: Dict[str, Any]) -> None:
        """Prints formatted exploration report conforming to STEP 7 specification."""
        print("\n==================================================")
        print("AUTONOMOUS EXPLORATION COMPLETE")
        print("==================================================")
        print(f"\nSteps: {summary['steps_count']}")
        print(f"Screens discovered: {summary['discovered_screens_count']}")
        print(f"Unique screens: {summary['unique_screens_count']}")
        print(f"Transitions: {summary['transitions_count']}")
        print(f"Successful actions: {summary['successful_actions']}")
        print(f"Failed actions: {summary['failed_actions']}")
        print(f"Safety-blocked actions: {summary['safety_blocked_actions']}")
        print(f"Termination reason: {summary['termination_reason']}")
        print(f"\nKnowledge Pack:\nartifacts/app_knowledge_pack.json")

        print("\nAlso print a compact exploration trace:\n")
        for entry in summary.get("trace", []):
            print(f"Step {entry['step']}:")
            print(f"{entry['source']}")
            print(f"→ {entry['action_desc']}")
            print(f"→ {entry['destination']}\n")
