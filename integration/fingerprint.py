"""
Screen Fingerprint module.

Generates deterministic fingerprints for ScreenState payloads to identify and
deduplicate screens without relying solely on Android Activity names.
"""

import hashlib
from typing import Any, Dict, List


def compute_screen_fingerprint(screen_state: Dict[str, Any]) -> str:
    """
    Computes a deterministic hash fingerprint representing the screen's UI state.

    Uses:
    - current_activity
    - sorted element IDs
    - element text and content-descriptions
    - interactive attributes (type, clickable, scrollable, enabled, bounds)

    Deterministic: Elements are sorted before hashing, ensuring that different
    dumpsys/UIAutomator traversal orderings of identical UI states produce the exact
    same fingerprint.

    :param screen_state: Standardized ScreenState dictionary.
    :return: Deterministic string fingerprint, e.g. 'state_a1b2c3d4e5f60718'.
    """
    if not isinstance(screen_state, dict):
        return "state_empty"

    activity = str(screen_state.get("current_activity", "") or "").strip()
    raw_elements = screen_state.get("elements", []) or []

    element_signatures: List[str] = []
    for elem in raw_elements:
        if not isinstance(elem, dict):
            continue

        el_id = str(elem.get("element_id", "") or "").strip()
        el_type = str(elem.get("type", "") or "").strip()
        text = str(elem.get("text", "") or "").strip()
        desc = str(elem.get("content_description", "") or "").strip()
        clickable = "1" if elem.get("clickable") else "0"
        scrollable = "1" if elem.get("scrollable") else "0"
        enabled = "1" if elem.get("enabled", True) else "0"

        bounds = elem.get("bounds")
        if isinstance(bounds, (list, tuple)) and len(bounds) == 4:
            bounds_str = f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}"
        else:
            bounds_str = ""

        sig = f"{el_id}|{el_type}|{text}|{desc}|{clickable}|{scrollable}|{enabled}|{bounds_str}"
        element_signatures.append(sig)

    # Sort deterministically to be independent of XML traversal order
    element_signatures.sort()

    payload = f"activity:{activity}\nelements:\n" + "\n".join(element_signatures)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"state_{digest}"
