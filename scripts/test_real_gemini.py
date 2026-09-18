"""
Real Gemini API test script for Zero-Touch App Understanding.

Verifies end-to-end reasoning pipeline:
    ReasoningContext -> Gemini -> LLMReasoner -> AgentAction

Uses GEMINI_API_KEY from the environment and NEVER prints the key.
Does NOT connect to Android.
"""

import os
import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.gemini_client import DEFAULT_GEMINI_MODEL, GeminiLLMClient, resolve_gemini_api_key
from agent.llm_reasoner import LLMReasoner
from agent.reasoning import ReasoningContext
from agent.semantic import ElementRole, ScreenType


def main() -> int:
    print("==================================================")
    print("Zero-Touch App Understanding - Real Gemini Test")
    print("==================================================")

    # 1. Resolve and verify GEMINI_API_KEY presence without printing its value
    api_key = resolve_gemini_api_key()
    if not api_key:
        print("[ERROR] GEMINI_API_KEY is not set in environment.")
        print("Please set the environment variable:")
        print("  Windows (PowerShell): $env:GEMINI_API_KEY = '<your-key>'")
        print("  Windows (CMD):        set GEMINI_API_KEY=<your-key>")
        print("  Linux/macOS:          export GEMINI_API_KEY='<your-key>'")
        return 1

    # Ensure current process environment has it
    os.environ["GEMINI_API_KEY"] = api_key
    print("[OK] GEMINI_API_KEY detected in environment (value hidden).")

    # 2. Configure model and initialize GeminiLLMClient
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    print(f"Connecting to Gemini with model: {model_name}...")

    try:
        gemini_client = GeminiLLMClient(model_name=model_name)
        reasoner = LLMReasoner(client=gemini_client)
    except Exception as exc:
        print(f"[ERROR] Failed to initialize Gemini client: {exc}")
        return 1

    # 3. Create synthetic ReasoningContext representing an Android screen
    context = ReasoningContext(
        screen_id="screen_settings_overview",
        screen_type=ScreenType.SETTINGS,
        likely_purpose="Configure Wi-Fi, display, and device preferences",
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
                "element_id": "com.android.settings:id/display_settings",
                "role": ElementRole.NAVIGATION,
                "label": "Display",
                "interaction": "tap",
                "clickable": True,
                "scrollable": False,
                "enabled": True,
                "explored": False,
            },
            {
                "element_id": "com.android.settings:id/search_box",
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
                "element_id": "com.android.settings:id/display_settings",
                "role": ElementRole.NAVIGATION,
                "label": "Display",
                "interaction": "tap",
            },
        ],
        recent_actions=[],
        recent_screens=[],
        exploration_step=1,
    )

    print("Dispatching ReasoningContext to Gemini via LLMReasoner...")

    # 4. Invoke LLMReasoner.decide
    try:
        action = reasoner.decide(context)
    except Exception as exc:
        print(f"[ERROR] Exception during Gemini decision: {exc}")
        return 1

    # 5. Output decision result
    print("\n==================================================")
    print("GEMINI REASONER DECISION RESULT:")
    print("==================================================")
    print(f"Action:       {action.action}")
    if action.target and action.target.element_id:
        print(f"Target ID:    {action.target.element_id}")
    else:
        print("Target ID:    None")
    print(f"Reason:       {action.reason or 'None'}")
    print("==================================================")
    print("Real Gemini test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
