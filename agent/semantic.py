"""
Semantic Screen Understanding module.

Provides deterministic, rule-based semantic classification of UI elements
and screens without external LLM dependencies.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class ElementRole:
    BUTTON = "button"
    TEXT_INPUT = "text_input"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    RADIO = "radio"
    IMAGE = "image"
    TEXT = "text"
    LIST_ITEM = "list_item"
    NAVIGATION = "navigation"
    SCROLL_CONTAINER = "scroll_container"
    UNKNOWN = "unknown"


class ScreenType:
    LOGIN = "login"
    SETTINGS = "settings"
    SEARCH = "search"
    UNKNOWN = "unknown"


def extract_label(element: Dict[str, Any]) -> str:
    """
    Extracts the most descriptive visible or accessibility label for an element.
    Prefers visible text; falls back to content_description.
    """
    text = str(element.get("text", "") or "").strip()
    if text:
        return text

    desc = str(element.get("content_description", "") or "").strip()
    if desc:
        return desc

    return ""


def classify_element_role(element: Dict[str, Any]) -> str:
    """
    Deterministically classifies a UI element into a controlled semantic role.
    """
    raw_type = str(element.get("type", "") or "").strip()
    type_lower = raw_type.lower()
    scrollable = bool(element.get("scrollable", False))
    clickable = bool(element.get("clickable", False))
    element_id = str(element.get("element_id", "") or "").lower()

    # 1. Scroll container
    if scrollable or any(
        cls in type_lower
        for cls in (
            "scrollview",
            "nestedscrollview",
            "recyclerview",
            "listview",
            "viewpager",
            "gridview",
        )
    ):
        return ElementRole.SCROLL_CONTAINER

    # 2. Switch
    if any(cls in type_lower for cls in ("switch", "switchcompat", "togglebutton")):
        return ElementRole.SWITCH

    # 3. Checkbox
    if "checkbox" in type_lower:
        return ElementRole.CHECKBOX

    # 4. Radio
    if "radiobutton" in type_lower or "radio" in type_lower:
        return ElementRole.RADIO

    # 5. Text Input
    if any(
        cls in type_lower
        for cls in (
            "edittext",
            "textinputedittext",
            "autocompletetextview",
            "searchautocomplete",
        )
    ) or type_lower in ("input", "text_input"):
        return ElementRole.TEXT_INPUT

    # 6. Button
    if any(
        cls in type_lower
        for cls in ("button", "imagebutton", "floatingactionbutton", "actionmenuitemview")
    ) or type_lower == "button":
        return ElementRole.BUTTON

    # 7. Navigation
    if any(
        cls in type_lower
        for cls in (
            "toolbar",
            "actionbar",
            "bottomnavigationview",
            "navigationview",
            "tablayout",
            "tabwidget",
        )
    ) or any(k in element_id for k in ("action_bar", "toolbar", "bottom_nav")):
        return ElementRole.NAVIGATION

    # 8. List / Card Item
    if any(cls in type_lower for cls in ("cardview", "listitem")) or "item" in type_lower:
        return ElementRole.LIST_ITEM

    # 9. Image
    if "imageview" in type_lower or type_lower == "image":
        if clickable:
            return ElementRole.BUTTON
        return ElementRole.IMAGE

    # 10. Text
    if "textview" in type_lower or type_lower == "text":
        if clickable:
            return ElementRole.BUTTON
        return ElementRole.TEXT

    # 11. Generic clickable element behaves as a button
    if clickable:
        return ElementRole.BUTTON

    return ElementRole.UNKNOWN


def determine_interaction(role: str, element: Dict[str, Any]) -> str:
    """
    Determines the primary expected interaction for a classified element.
    """
    if role in (
        ElementRole.BUTTON,
        ElementRole.CHECKBOX,
        ElementRole.SWITCH,
        ElementRole.RADIO,
        ElementRole.LIST_ITEM,
    ):
        return "tap"

    if role == ElementRole.TEXT_INPUT:
        return "type"

    if role == ElementRole.SCROLL_CONTAINER:
        return "scroll"

    if element.get("clickable"):
        return "tap"

    return "none"


def classify_element(element: Dict[str, Any]) -> Dict[str, Any]:
    """
    Augments an element dictionary with deterministic semantic metadata
    (role, label, interaction) while strictly preserving all raw original fields.
    """
    enriched = dict(element)
    role = classify_element_role(element)
    label = extract_label(element)
    interaction = determine_interaction(role, element)

    enriched["role"] = role
    enriched["label"] = label
    enriched["interaction"] = interaction
    return enriched


@dataclass
class ScreenUnderstanding:
    """
    Structured semantic understanding of an Android screen.
    """
    screen_id: str
    screen_type: str
    likely_purpose: str
    important_elements: List[Dict[str, Any]] = field(default_factory=list)
    elements: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "screen_type": self.screen_type,
            "likely_purpose": self.likely_purpose,
            "important_elements": self.important_elements,
            "elements": self.elements,
        }


def analyze_screen(screen_data: Dict[str, Any]) -> ScreenUnderstanding:
    """
    Analyzes an observed screen and derives high-level screen semantics,
    likely purpose, and primary important elements.
    """
    screen_id = str(screen_data.get("screen_id", "") or "screen_unknown")
    activity = str(screen_data.get("current_activity", "") or "").lower()
    raw_elements = screen_data.get("elements", []) or []

    # 1. Classify all elements
    classified_elements = [classify_element(elem) for elem in raw_elements if isinstance(elem, dict)]

    # 2. Extract feature counts and cues
    switches = [e for e in classified_elements if e["role"] == ElementRole.SWITCH]
    inputs = [e for e in classified_elements if e["role"] == ElementRole.TEXT_INPUT]
    buttons = [e for e in classified_elements if e["role"] == ElementRole.BUTTON]

    all_labels_lower = [
        f"{e['label']} {e.get('element_id', '')}".lower() for e in classified_elements
    ]
    all_text_blob = " ".join(all_labels_lower)

    screen_type = ScreenType.UNKNOWN
    likely_purpose = ""
    important_elements: List[Dict[str, Any]] = []

    # 3. Deterministic classification heuristics

    # A. LOGIN SCREEN CHECK
    has_password_input = any(
        any(k in e.get("element_id", "").lower() or k in e["label"].lower() for k in ("password", "pass", "pwd"))
        for e in inputs
    )
    has_user_input = any(
        any(k in e.get("element_id", "").lower() or k in e["label"].lower() for k in ("username", "user", "email", "phone", "account"))
        for e in inputs
    )
    has_login_button = any(
        any(k in b["label"].lower() or k in b.get("element_id", "").lower() for k in ("login", "sign in", "signin", "log in"))
        for b in buttons
    )
    is_login_activity = any(k in activity for k in ("login", "signin", "auth"))

    if (has_password_input and (has_login_button or has_user_input)) or (is_login_activity and inputs):
        screen_type = ScreenType.LOGIN
        likely_purpose = "User authentication and sign in"
        important_elements = [e for e in inputs] + [
            b for b in buttons if any(k in b["label"].lower() or k in b.get("element_id", "").lower() for k in ("login", "sign", "submit"))
        ]

    # B. SEARCH SCREEN CHECK
    elif not screen_type or screen_type == ScreenType.UNKNOWN:
        has_search_input = any(
            any(k in e.get("element_id", "").lower() or k in e["label"].lower() for k in ("search", "query", "find"))
            for e in inputs
        )
        is_search_activity = "search" in activity

        if has_search_input or (is_search_activity and (inputs or any("search" in b["label"].lower() for b in buttons))):
            screen_type = ScreenType.SEARCH
            likely_purpose = "Search and content discovery"
            important_elements = [
                e for e in inputs if any(k in e.get("element_id", "").lower() or k in e["label"].lower() for k in ("search", "query", "find"))
            ] + [
                b for b in buttons if any(k in b["label"].lower() or k in b.get("element_id", "").lower() for k in ("search", "go", "submit"))
            ]

    # C. SETTINGS SCREEN CHECK
    if screen_type == ScreenType.UNKNOWN:
        settings_keywords = (
            "wifi",
            "wi-fi",
            "bluetooth",
            "display",
            "sound",
            "battery",
            "storage",
            "privacy",
            "security",
            "notification",
            "network",
            "account",
            "preference",
        )
        matching_settings_cues = sum(1 for kw in settings_keywords if kw in all_text_blob)
        is_settings_activity = any(k in activity for k in ("setting", "preference"))

        if len(switches) >= 2 or (is_settings_activity and (switches or matching_settings_cues >= 1)) or matching_settings_cues >= 2:
            screen_type = ScreenType.SETTINGS
            likely_purpose = "Application settings and configuration"
            important_elements = switches + [
                e for e in classified_elements if e["role"] in (ElementRole.CHECKBOX, ElementRole.BUTTON, ElementRole.LIST_ITEM) and any(kw in f"{e['label']} {e.get('element_id', '')}".lower() for kw in settings_keywords)
            ]

    # D. UNKNOWN FALLBACK
    if screen_type == ScreenType.UNKNOWN:
        screen_type = ScreenType.UNKNOWN
        likely_purpose = ""
        # Default important elements: labeled interactive elements
        important_elements = [
            e for e in classified_elements if e.get("clickable") and e.get("label")
        ][:5]

    return ScreenUnderstanding(
        screen_id=screen_id,
        screen_type=screen_type,
        likely_purpose=likely_purpose,
        important_elements=important_elements,
        elements=classified_elements,
    )
