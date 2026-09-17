"""
Type definitions for the Exploration Agent.
"""

from typing import Literal, Optional, Any
from dataclasses import dataclass, field


ActionType = Literal["tap", "back", "scroll", "wait", "stop"]


@dataclass
class ActionTarget:
    element_id: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.element_id is not None:
            result["element_id"] = self.element_id
        if self.extra:
            result.update(self.extra)
        return result


@dataclass
class AgentAction:
    action: ActionType
    target: Optional[ActionTarget] = None

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {"action": self.action}
        if self.target is not None and self.target.to_dict():
            res["target"] = self.target.to_dict()
        return res
