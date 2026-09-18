"""
Safety validation layer for autonomous app exploration.

Provides conservative guardrails against executing potentially destructive,
financial, or irreversible actions during automated discovery.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

# Conservative patterns identifying risky / destructive actions
DEFAULT_RISKY_PATTERNS: Set[str] = {
    "delete",
    "remove",
    "uninstall",
    "erase",
    "clear data",
    "format",
    "purchase",
    "buy now",
    "pay",
    "checkout",
    "transfer",
    "send",
    "send money",
    "submit",
    "confirm deletion",
    "factory reset",
    "wipe",
}


@dataclass
class ValidationResult:
    """Outcome of action safety evaluation."""
    allowed: bool
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
        }


class SafetyValidator:
    """Evaluates agent actions against conservative exploration safety policies."""

    def __init__(
        self,
        risky_patterns: Optional[Set[str]] = None,
        allow_risky: bool = False,
    ) -> None:
        self.risky_patterns = set(risky_patterns or DEFAULT_RISKY_PATTERNS)
        self.allow_risky = allow_risky

    def is_risky_text(self, text: str) -> bool:
        """Checks if a string contains any conservative risky pattern."""
        if not text:
            return False
        clean = text.lower().strip()
        for pattern in self.risky_patterns:
            if pattern in clean:
                return True
        return False

    def validate_action(
        self,
        action: Any,
        context: Optional[Any] = None,
    ) -> ValidationResult:
        """
        Validates whether an action is safe to execute.

        :param action: AgentAction dataclass or action dictionary.
        :param context: Optional ReasoningContext or dict containing screen elements.
        :return: ValidationResult with allowed flag and explanation.
        """
        if self.allow_risky:
            return ValidationResult(allowed=True, reason=None)

        if isinstance(action, dict):
            action_name = str(action.get("action", "")).lower()
            target = action.get("target") or {}
            element_id = str(target.get("element_id", "") or "")
        else:
            action_name = str(getattr(action, "action", "") or "").lower()
            target = getattr(action, "target", None)
            element_id = str(getattr(target, "element_id", "") if target else "")

        # System actions are intrinsically safe
        if action_name in ("back", "wait", "stop"):
            return ValidationResult(allowed=True, reason=None)

        # Check action name itself for risky terms
        if self.is_risky_text(action_name):
            return ValidationResult(
                allowed=False,
                reason=f"Action '{action_name}' matches safety policy pattern",
            )

        # Check target element ID for risky terms
        if self.is_risky_text(element_id):
            return ValidationResult(
                allowed=False,
                reason=f"Target element ID '{element_id}' matches safety policy pattern",
            )

        # Check element label and metadata in context if available
        if context is not None:
            raw_elements = (
                getattr(context, "elements", [])
                if not isinstance(context, dict)
                else context.get("elements", [])
            )
            for elem in raw_elements:
                e_id = (
                    elem.get("element_id", "")
                    if isinstance(elem, dict)
                    else getattr(elem, "element_id", "")
                )
                if e_id == element_id:
                    label = (
                        elem.get("label", "")
                        if isinstance(elem, dict)
                        else getattr(elem, "label", "")
                    )
                    text = (
                        elem.get("text", "")
                        if isinstance(elem, dict)
                        else getattr(elem, "text", "")
                    )
                    desc = (
                        elem.get("content_description", "")
                        if isinstance(elem, dict)
                        else getattr(elem, "content_description", "")
                    )

                    for candidate in (label, text, desc):
                        if self.is_risky_text(candidate):
                            return ValidationResult(
                                allowed=False,
                                reason=f"Potentially destructive action: label '{candidate}' matches safety pattern",
                            )
                    break

        return ValidationResult(allowed=True, reason=None)


def validate_action(action: Any, context: Optional[Any] = None) -> ValidationResult:
    """Convenience validation function using default SafetyValidator."""
    return SafetyValidator().validate_action(action, context)
