"""
Validation script for ZeroTouch Demo Knowledge Pack.
"""

import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from knowledge.builder import KnowledgeBuilder, validate_knowledge_pack
from knowledge.models import AppKnowledgePack


def run_validation():
    pack_path = os.path.join(PROJECT_ROOT, "artifacts", "zerotouch_demo_knowledge_pack.json")
    if not os.path.exists(pack_path):
        print(f"[ERROR] Knowledge pack not found at {pack_path}")
        return 1

    with open(pack_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 1. Serialization / Deserialization check
    try:
        pack = AppKnowledgePack.from_dict(raw_data)
        print("[OK] Serialized JSON successfully loaded and parsed into AppKnowledgePack.")
    except Exception as exc:
        print(f"[FAIL] Deserialization failed: {exc}")
        return 1

    # 2. Built-in KnowledgeBuilder validation
    val_result = validate_knowledge_pack(pack)
    print(f"\nKnowledge pack validation:")
    print(f"  Valid: {val_result.get('valid')}")
    print(f"  Element errors: {len(val_result.get('element_errors', []))}")
    print(f"  Transition errors: {len(val_result.get('transition_errors', []))}")

    # 3. Screens & Elements count
    total_screens = len(pack.screens)
    total_elements = sum(len(s.elements) for s in pack.screens.values())
    print(f"\nUnique screens discovered: {total_screens}")
    print(f"Total UI elements discovered: {total_elements}")

    for s_id, s in pack.screens.items():
        print(f"  Screen [{s_id[:12]}]: {s.name} | Activity: {s.activity_name} | Elements: {len(s.elements)} | Purpose: {s.purpose}")

    # 4. Transitions count & graph integrity
    top_transitions = len(pack.transitions)
    graph_transitions = len(pack.navigation_graph.transitions) if hasattr(pack.navigation_graph, "transitions") else len(pack.navigation_graph.get("transitions", []))
    graph_edges = len(pack.navigation_graph.edges) if hasattr(pack.navigation_graph, "edges") else len(pack.navigation_graph.get("edges", []))
    graph_nodes = len(pack.navigation_graph.nodes) if hasattr(pack.navigation_graph, "nodes") else len(pack.navigation_graph.get("nodes", []))

    print(f"\nTransitions:")
    print(f"  Top-level transitions: {top_transitions}")
    print(f"  Navigation graph transitions: {graph_transitions}")
    print(f"  Navigation graph edges: {graph_edges}")
    print(f"  Navigation graph nodes: {graph_nodes}")

    for t in pack.transitions:
        print(f"  - {t.transition_id}: {t.source_screen_id[:10]} -> {t.destination_screen_id[:10]} | action={t.action.action_type} target={t.action.target_element_id}")

    # 5. Duplicate screen check
    print("\nIntegrity Checks:")
    seen_screens = set()
    dup_screens = 0
    for s_id in pack.screens.keys():
        if s_id in seen_screens:
            dup_screens += 1
        seen_screens.add(s_id)
    print(f"  Duplicate screens: {dup_screens}")

    # 6. Element identity collisions
    collisions = 0
    for s_id, s in pack.screens.items():
        seen_el = set()
        for el in s.elements:
            if el.element_id in seen_el:
                collisions += 1
                print(f"  [COLLISION] screen {s_id}: element {el.element_id}")
            seen_el.add(el.element_id)
    print(f"  Element identity collisions: {collisions}")

    # 7. Semantic label mismatches
    mismatches = 0
    for s_id, s in pack.screens.items():
        for el in s.elements:
            if el.text and "label=" in el.purpose:
                label = el.purpose.split("label=")[1].split(";")[0].strip()
                if label and el.text.strip():
                    if label != el.text.strip() and label not in el.text and el.text not in label:
                        mismatches += 1
                        print(f"  [MISMATCH] {s_id} [{el.element_id}]: text='{el.text}' vs label='{label}'")
    print(f"  Semantic label mismatches: {mismatches}")

    # 8. Valid transition references
    orphans = 0
    for t in pack.transitions:
        if t.source_screen_id not in pack.screens:
            orphans += 1
            print(f"  [ORPHAN SOURCE] {t.source_screen_id}")
        if t.destination_screen_id not in pack.screens:
            orphans += 1
            print(f"  [ORPHAN DEST] {t.destination_screen_id}")
    print(f"  Orphan transition references: {orphans}")

    # 9. Target element reference validity
    invalid_targets = 0
    for t in pack.transitions:
        target_id = t.action.target_element_id
        if target_id and t.action.action_type in ("tap", "type"):
            source_screen = pack.screens.get(t.source_screen_id)
            if source_screen:
                screen_el_ids = {e.element_id for e in source_screen.elements}
                if target_id not in screen_el_ids:
                    invalid_targets += 1
                    print(f"  [INVALID TARGET] Action {t.action.action_id} targets {target_id} not on screen {t.source_screen_id}")
    print(f"  Invalid action target elements: {invalid_targets}")

    has_errors = (
        not val_result.get("valid", False)
        or len(val_result.get("element_errors", [])) > 0
        or len(val_result.get("transition_errors", [])) > 0
        or collisions > 0
        or mismatches > 0
        or orphans > 0
        or invalid_targets > 0
    )

    if has_errors:
        print("\n[RESULT] Validation FAILED with errors.")
        return 1
    else:
        print("\n[RESULT] All validations PASSED with 0 errors!")
        return 0


if __name__ == "__main__":
    sys.exit(run_validation())
