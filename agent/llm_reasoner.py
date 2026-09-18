"""
Provider-neutral LLM reasoning adapter for autonomous Android app exploration.

Transforms compact ReasoningContext into a structured exploration prompt,
invokes a provider-neutral model client, strictly validates model output,
and provides safe fallback actions for any failures, hallucinations, or safety violations.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, Set, Union

from .reasoning import BaseReasoner, ReasoningContext
from .safety import SafetyValidator, validate_action
from .semantic import ElementRole
from .types import ActionTarget, ActionType, AgentAction

ALLOWED_ACTIONS: Set[str] = {"tap", "type", "scroll", "back", "wait", "stop"}


def extract_json_object(text: str) -> str:
    """Extracts a JSON object string from raw model output or markdown code blocks."""
    text = text.strip()
    # Check for markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    # Find the outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text


def build_reasoning_prompt(context: ReasoningContext) -> str:
    """
    Constructs a deterministic, compact prompt for LLM exploration reasoning.
    Contains only semantic information; excludes raw UI XML tree and bounds data.
    """
    # Format semantic elements
    elements_lines = []
    for elem in context.elements:
        el_id = elem.get("element_id", "")
        role = elem.get("role", "unknown")
        label = elem.get("label", "")
        interaction = elem.get("interaction", "none")
        enabled = elem.get("enabled", True)
        explored = elem.get("explored", False)

        parts = [f"id='{el_id}'", f"role='{role}'"]
        if label:
            parts.append(f"label='{label}'")
        parts.append(f"interaction='{interaction}'")
        parts.append(f"enabled={enabled}")
        parts.append(f"explored={explored}")
        elements_lines.append("  - " + ", ".join(parts))

    elements_text = "\n".join(elements_lines) if elements_lines else "  (None)"

    # Format available interactions
    avail_lines = []
    for item in context.available_interactions:
        avail_lines.append(
            f"  - id='{item.get('element_id', '')}', role='{item.get('role', '')}', "
            f"label='{item.get('label', '')}', interaction='{item.get('interaction', '')}'"
        )
    avail_text = "\n".join(avail_lines) if avail_lines else "  (No unexplored safe interactions)"

    # Format recent history
    recent_screens_str = (
        ", ".join(context.recent_screens) if context.recent_screens else "None"
    )

    recent_actions_lines = []
    for act in context.recent_actions:
        a_name = act.get("action", "")
        t_id = act.get("element_id") or ""
        recent_actions_lines.append(f"  - action={a_name}, element_id={t_id}")
    recent_actions_str = (
        "\n".join(recent_actions_lines) if recent_actions_lines else "  (None)"
    )

    prompt = f"""You are an autonomous AI agent exploring an unfamiliar Android application to understand its functionality.
Your goal is to systematically discover application features while avoiding destructive or irreversible actions.

SCREEN INFORMATION:
- Screen ID: {context.screen_id}
- Screen Type: {context.screen_type}
- Likely Purpose: {context.likely_purpose}
- Foreground Activity: {context.current_activity}
- Exploration Step: {context.exploration_step}

NAVIGATION & ACTION HISTORY:
- Recent Screens: {recent_screens_str}
- Recent Actions:
{recent_actions_str}

SEMANTIC UI ELEMENTS:
{elements_text}

AVAILABLE UNEXPLORED INTERACTIONS:
{avail_text}

EXPLORATION INSTRUCTIONS:
1. Explore unfamiliar apps systematically and thoroughly.
2. PREFER UNEXPLORED CONTROLS ON CURRENT SCREEN: On each screen, identify meaningful unexplored interactive elements from AVAILABLE UNEXPLORED INTERACTIONS. You MUST prioritize unexplored navigation/actions on the current application screen (such as search, navigation buttons, or items) before choosing 'back'.
3. CRITICAL: Do NOT choose action 'back' if there are still meaningful unexplored interactive controls remaining on the current application screen.
4. Only choose action 'back' when:
   - There are NO meaningful unexplored actions remaining on the current screen, OR
   - The current screen is otherwise exhausted.
5. Avoid destructive or irreversible actions (e.g., delete, remove, uninstall, purchase, pay, checkout, transfer, send, submit, factory reset).
6. NEVER invent element IDs or coordinates. Only select an element_id that explicitly exists in the SEMANTIC UI ELEMENTS list above.
7. Do NOT target disabled or already-explored elements.
8. If exploration is complete or terminal, use action 'stop'.
9. In controlled demo/test environments requiring input, use safe test credentials (e.g. 'test@zerotouch.com' for email, 'demo123' for password, or safe catalog search terms like 'Headphones'). Do NOT use real personal credentials.
10. Do NOT make assumptions about unavailable UI elements.

REQUIRED OUTPUT FORMAT:
Respond strictly with a single valid JSON object. Do not include explanatory text outside the JSON object:
{{
  "action": "tap" | "type" | "scroll" | "back" | "wait" | "stop",
  "target": {{
    "element_id": "<exact element_id from list above>",
    "text": "<optional text if action is type>"
  }},
  "reason": "<short concise explanation for your decision>"
}}"""

    return prompt


class FakeLLMClient:
    """Mock LLM client for deterministic, offline testing."""

    def __init__(
        self,
        responses: Optional[Union[str, List[str], Dict[str, Any], List[Dict[str, Any]]]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        self.call_count = 0
        self.last_prompt: Optional[str] = None
        self.exception = exception
        if responses is None:
            self._responses: List[str] = []
        elif isinstance(responses, (str, dict)):
            self._responses = [self._normalize_response(responses)]
        else:
            self._responses = [self._normalize_response(r) for r in responses]

    @staticmethod
    def _normalize_response(resp: Union[str, Dict[str, Any]]) -> str:
        if isinstance(resp, dict):
            return json.dumps(resp)
        return str(resp)

    def set_response(self, response: Union[str, Dict[str, Any]]) -> None:
        self._responses = [self._normalize_response(response)]
        self.exception = None

    def set_responses(self, responses: List[Union[str, Dict[str, Any]]]) -> None:
        self._responses = [self._normalize_response(r) for r in responses]
        self.exception = None

    def set_exception(self, exception: Exception) -> None:
        self.exception = exception

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        if self.exception is not None:
            raise self.exception
        if not self._responses:
            return json.dumps({"action": "back", "reason": "Default fake response"})
        if self.call_count <= len(self._responses):
            return self._responses[self.call_count - 1]
        return self._responses[-1]

    def __call__(self, prompt: str, **kwargs: Any) -> str:
        return self.generate(prompt, **kwargs)


class LLMReasoner(BaseReasoner):
    """
    Provider-neutral AI model reasoner adhering to BaseReasoner interface.

    Accepts an external client (callable or object with .generate / .complete),
    generates a compact semantic prompt, and strictly validates all model outputs.
    """

    def __init__(
        self,
        client: Any,
        model_name: Optional[str] = None,
        timeout: float = 30.0,
        safety_validator: Optional[SafetyValidator] = None,
    ) -> None:
        self.client = client
        self.model_name = model_name
        self.timeout = timeout
        self.safety_validator = safety_validator or SafetyValidator()

    def _invoke_client(self, prompt: str) -> str:
        """Invokes the client in a provider-neutral manner."""
        if self.client is None:
            raise ValueError("No model client configured")

        if hasattr(self.client, "generate"):
            res = self.client.generate(prompt)
        elif hasattr(self.client, "complete"):
            res = self.client.complete(prompt)
        elif callable(self.client):
            res = self.client(prompt)
        else:
            raise TypeError(
                "Model client must be callable or provide a generate/complete method"
            )

        if isinstance(res, str):
            return res
        if hasattr(res, "text"):
            return str(res.text)
        if hasattr(res, "content"):
            return str(res.content)
        return str(res)

    def parse_and_validate(
        self,
        raw_output: str,
        context: ReasoningContext,
    ) -> AgentAction:
        """
        Parses raw model response and strictly validates it against current context and safety policies.
        Returns a validated AgentAction or a safe fallback ('back').
        """
        json_str = extract_json_object(raw_output)

        try:
            parsed = json.loads(json_str)
        except Exception:
            return AgentAction(
                action="back",
                reason="AI decision rejected: malformed JSON response",
            )

        if not isinstance(parsed, dict):
            return AgentAction(
                action="back",
                reason="AI decision rejected: model response is not a JSON object",
            )

        action_name = str(parsed.get("action", "") or "").lower().strip()
        if not action_name:
            return AgentAction(
                action="back",
                reason="AI decision rejected: missing 'action' field in model response",
            )

        if action_name not in ALLOWED_ACTIONS:
            return AgentAction(
                action="back",
                reason=f"AI decision rejected: unsupported action '{action_name}'",
            )

        reason = parsed.get("reason")
        if reason:
            reason = str(reason).strip()

        # System / non-target actions are validated directly
        if action_name in ("back", "wait", "stop"):
            action_obj = AgentAction(
                action=action_name,  # type: ignore[arg-type]
                reason=reason or f"AI decision: execute {action_name}",
            )
            # Validate safety
            val = self.safety_validator.validate_action(action_obj, context)
            if not val.allowed:
                return AgentAction(
                    action="back",
                    reason=f"AI decision rejected by safety policy: {val.reason}",
                )
            return action_obj

        # Interactive actions require a target
        target_dict = parsed.get("target")
        if not isinstance(target_dict, dict):
            return AgentAction(
                action="back",
                reason=f"AI decision rejected: action '{action_name}' requires a target dictionary",
            )

        # Coordinate invention check: Reject coordinates
        for coord_key in ("x", "y", "bounds", "coordinates", "coords"):
            if coord_key in target_dict and not target_dict.get("element_id"):
                return AgentAction(
                    action="back",
                    reason="AI decision rejected: coordinate targets not permitted",
                )

        element_id = str(target_dict.get("element_id", "") or "").strip()
        if not element_id:
            return AgentAction(
                action="back",
                reason=f"AI decision rejected: action '{action_name}' missing target element_id",
            )

        # Validate that element actually exists in the supplied context
        matching_elem = next(
            (e for e in context.elements if e.get("element_id") == element_id),
            None,
        )
        if matching_elem is None:
            return AgentAction(
                action="back",
                reason=f"AI decision rejected: element '{element_id}' does not exist on screen",
            )

        # Validate enabled status
        if not matching_elem.get("enabled", True):
            return AgentAction(
                action="back",
                reason=f"AI decision rejected: element '{element_id}' is disabled",
            )

        # Validate action compatibility
        if action_name == "type":
            is_type_compatible = (
                matching_elem.get("role") == ElementRole.TEXT_INPUT
                or matching_elem.get("interaction") == "type"
                or matching_elem.get("role") == "text_input"
            )
            if not is_type_compatible:
                return AgentAction(
                    action="back",
                    reason=f"AI decision rejected: element '{element_id}' does not support type action",
                )

        if action_name == "scroll":
            is_scroll_compatible = (
                matching_elem.get("scrollable", False)
                or matching_elem.get("interaction") == "scroll"
                or matching_elem.get("role") == ElementRole.SCROLL_CONTAINER
                or matching_elem.get("role") == "scroll_container"
            )
            if not is_scroll_compatible:
                return AgentAction(
                    action="back",
                    reason=f"AI decision rejected: element '{element_id}' does not support scroll action",
                )

        if action_name == "tap":
            is_tap_compatible = (
                matching_elem.get("clickable", False)
                or matching_elem.get("interaction") in ("tap", "type")
                or matching_elem.get("role")
                in (
                    ElementRole.BUTTON,
                    ElementRole.NAVIGATION,
                    ElementRole.LIST_ITEM,
                    ElementRole.CHECKBOX,
                    ElementRole.SWITCH,
                    ElementRole.RADIO,
                    ElementRole.IMAGE,
                    ElementRole.TEXT,
                )
            )
            if not is_tap_compatible:
                return AgentAction(
                    action="back",
                    reason=f"AI decision rejected: element '{element_id}' is not actionable for tap",
                )

        # Construct target
        extra: Dict[str, Any] = {}
        if action_name == "type" and "text" in target_dict:
            extra["text"] = str(target_dict["text"])

        action_obj = AgentAction(
            action=action_name,  # type: ignore[arg-type]
            target=ActionTarget(element_id=element_id, extra=extra),
            reason=reason or f"AI decision: {action_name} on '{element_id}'",
        )

        # Safety validation
        val = self.safety_validator.validate_action(action_obj, context)
        if not val.allowed:
            return AgentAction(
                action="back",
                reason=f"AI decision rejected by safety policy: {val.reason}",
            )

        return action_obj

    def decide(self, context: ReasoningContext) -> AgentAction:
        """
        Invokes the AI model with the generated prompt, parses and validates the response,
        and returns an AgentAction. All errors and invalid decisions fall back safely to 'back'.
        """
        prompt = build_reasoning_prompt(context)
        try:
            raw_response = self._invoke_client(prompt)
        except Exception as exc:
            return AgentAction(
                action="back",
                reason=f"AI decision rejected: model client error ({type(exc).__name__}: {str(exc)})",
            )

        return self.parse_and_validate(raw_response, context)
