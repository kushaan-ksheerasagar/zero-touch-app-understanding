"""
Interactive demonstration of the Exploration Agent.

Simulates screen exploration step-by-step to demonstrate:
1. Identifying clickable buttons.
2. Avoiding repeated actions on subsequent visits.
3. Returning 'back' when all buttons have been explored.
"""

import json
from agent import ExplorationAgent


def run_demo():
    print("=" * 60)
    print("         EXPLORATION AGENT - PHASE 1 DEMO")
    print("=" * 60)

    agent = ExplorationAgent()

    home_screen = {
        "screen_id": "home",
        "elements": [
            {
                "element_id": "search_button",
                "type": "button",
                "text": "Search",
                "clickable": True,
            },
            {
                "element_id": "profile_button",
                "type": "button",
                "text": "Profile",
                "clickable": True,
            },
        ],
    }

    print("\n[Screen Provided to Agent]")
    print(json.dumps(home_screen, indent=2))

    for step_num in range(1, 4):
        print(f"\n--- Step {step_num} ---")
        action = agent.step(home_screen)
        print("Agent Decided Action:")
        print(json.dumps(action, indent=2))

        attempted = agent.get_memory().get_attempted_elements("home")
        print(f"Memory (attempted elements on 'home'): {list(attempted)}")

    print("\nDemo completed successfully.")


if __name__ == "__main__":
    run_demo()
