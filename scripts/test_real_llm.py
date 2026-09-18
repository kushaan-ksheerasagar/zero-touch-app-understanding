"""
Manual live API smoke test script for GroqLLMClient + LLMReasoner.

Verifies end-to-end integration:
    ReasoningContext -> Groq -> LLMReasoner -> AgentAction

DO NOT RUN AUTOMATICALLY during automated testing.
Run manually only when GROQ_API_KEY is configured in the environment.
"""

import os
import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.groq_client import DEFAULT_GROQ_MODEL, GroqLLMClient
from agent.llm_reasoner import LLMReasoner
from agent.reasoning import ReasoningContext
from agent.semantic import ElementRole, ScreenType


def main() -> int:
    print("==================================================")
    print("Zero-Touch App Understanding - Real LLM Smoke Test")
    print("==================================================")

    # 1. Check GROQ_API_KEY presence without printing its value
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        print("[ERROR] GROQ_API_KEY is not set in environment.")
        print("Please set the environment variable and try again:")
        print("  Windows (PowerShell): $env:GROQ_API_KEY = '<your-key>'")
        print("  Windows (CMD):        set GROQ_API_KEY=<your-key>")
        print("  Linux/macOS:          export GROQ_API_KEY='<your-key>'")
        return 1

    print("[OK] GROQ_API_KEY detected in environment (value hidden).")

    # 2. Create GroqLLMClient & LLMReasoner
    model_name = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    print(f"Connecting to Groq with model: {model_name}...")

    try:
        groq_client = GroqLLMClient(model_name=model_name)
        reasoner = LLMReasoner(client=groq_client)
    except Exception as exc:
        print(f"[ERROR] Failed to initialize Groq client: {exc}")
        return 1

    # 3. Create a synthetic ReasoningContext
    context = ReasoningContext(
        screen_id="screen_settings_demo",
        screen_type=ScreenType.SETTINGS,
        likely_purpose="Configure Wi-Fi, Bluetooth, and device preferences",
        current_activity="com.android.settings.SettingsActivity",
        elements=[
            {
                "element_id": "com.android.settings:id/network_and_internet",
                "role": ElementRole.NAVIGATION,
                "label": "Network & internet",
                "interaction": "tap",
                "clickable": True,
                "scrollable": False,
                "enabled": True,
                "explored": False,
            },
            {
                "element_id": "com.android.settings:id/connected_devices",
                "role": ElementRole.NAVIGATION,
                "label": "Connected devices",
                "interaction": "tap",
                "clickable": True,
                "scrollable": False,
                "enabled": True,
                "explored": False,
            },
            {
                "element_id": "com.android.settings:id/search_action_bar",
                "role": ElementRole.TEXT_INPUT,
                "label": "Search settings",
                "interaction": "type",
                "clickable": True,
                "scrollable": False,
                "enabled": True,
                "explored": False,
            },
        ],
        explored_element_ids=[],
        available_interactions=[
            {
                "element_id": "com.android.settings:id/network_and_internet",
                "role": ElementRole.NAVIGATION,
                "label": "Network & internet",
                "interaction": "tap",
            },
            {
                "element_id": "com.android.settings:id/connected_devices",
                "role": ElementRole.NAVIGATION,
                "label": "Connected devices",
                "interaction": "tap",
            },
        ],
        recent_actions=[],
        recent_screens=[],
        exploration_step=1,
    )

    print("Dispatching synthetic ReasoningContext to Groq via LLMReasoner...")

    # 4. Call LLMReasoner
    try:
        action = reasoner.decide(context)
    except Exception as exc:
        print(f"[ERROR] Exception during LLM decision: {exc}")
        return 1

    # 5. Print readable report
    print("\n==================================================")
    print("REASONER DECISION RESULT:")
    print("==================================================")
    print(f"Action:       {action.action}")
    if action.target and action.target.element_id:
        print(f"Target ID:    {action.target.element_id}")
    else:
        print("Target ID:    None")
    print(f"Reason:       {action.reason or 'None'}")
    print("==================================================")
    print("Live API Smoke Test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
