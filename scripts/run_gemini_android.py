"""
Real Gemini -> Android Autonomous Exploration Smoke Test.

Connects the real Gemini LLM backend to a running Android emulator/device
to execute exactly ONE autonomous, safety-validated exploration action.
"""

import os
import shutil
import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 1. Ensure project root and android-controller are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_CONTROLLER_DIR = os.path.join(PROJECT_ROOT, "android-controller")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if ANDROID_CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, ANDROID_CONTROLLER_DIR)

# Ensure Android SDK platform-tools is available on PATH for adb discovery
sdk_platform_tools = os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools")
if os.path.exists(sdk_platform_tools) and sdk_platform_tools not in os.environ.get("PATH", ""):
    os.environ["PATH"] = sdk_platform_tools + os.pathsep + os.environ.get("PATH", "")

from agent.gemini_client import DEFAULT_GEMINI_MODEL, GeminiLLMClient, resolve_gemini_api_key
from agent.llm_reasoner import LLMReasoner
from agent.reasoning import build_reasoning_context
from agent.safety import SafetyValidator
from agent.semantic import analyze_screen
from controller import AndroidController
from integration.adapters import to_api_screen_state, to_controller_action
from integration.fingerprint import compute_screen_fingerprint

ALLOWED_SMOKE_ACTIONS = {"tap", "scroll", "back", "wait"}


def main() -> int:
    # 1. Verify GEMINI_API_KEY without printing it
    api_key = resolve_gemini_api_key()
    if not api_key:
        print("[ERROR] GEMINI_API_KEY environment variable is not set.")
        print("Please set it in your environment before running this script:")
        print("  Windows (PowerShell): $env:GEMINI_API_KEY = '<your-key>'")
        print("  Windows (CMD):        set GEMINI_API_KEY=<your-key>")
        print("  Linux/macOS:          export GEMINI_API_KEY='<your-key>'")
        return 1

    os.environ["GEMINI_API_KEY"] = api_key

    # 2. Check ZERO_TOUCH_PACKAGE configuration
    package_name = os.environ.get("ZERO_TOUCH_PACKAGE")
    activity_name = os.environ.get("ZERO_TOUCH_ACTIVITY")

    if not package_name or not package_name.strip():
        print("[ERROR] ZERO_TOUCH_PACKAGE environment variable is not set.")
        print("Please specify the target Android package to explore:")
        print("  Windows (PowerShell): $env:ZERO_TOUCH_PACKAGE = 'com.android.settings'")
        print("  Windows (CMD):        set ZERO_TOUCH_PACKAGE=com.android.settings")
        print("  Linux/macOS:          export ZERO_TOUCH_PACKAGE='com.android.settings'")
        return 1

    package_name = package_name.strip()
    target_device = os.environ.get("ANDROID_DEVICE_ID", "emulator-5554")

    print("==================================================")
    print("GEMINI → ANDROID REAL SMOKE TEST")
    print("==================================================")
    print(f"\nDevice: {target_device}")
    print(f"App: {package_name}")

    # 3. Connect to Android Controller
    try:
        controller = AndroidController()
        connected_id = controller.connect(device_id=target_device)
    except Exception as exc:
        print(f"\n[ERROR] Failed to connect to Android device '{target_device}': {exc}")
        return 1

    # 4. Launch the target app
    try:
        raw_initial_state = controller.launch_app(package_name, activity_name=activity_name)
    except Exception as exc:
        print(f"\n[ERROR] Failed to launch application '{package_name}': {exc}")
        return 1

    # 5. Capture current ScreenState and compute fingerprint
    initial_api_state = to_api_screen_state(raw_initial_state)
    initial_fingerprint = compute_screen_fingerprint(initial_api_state)
    activity_found = initial_api_state.get("current_activity", "unknown")
    element_count = len(initial_api_state.get("elements", []))

    print("\nCurrent screen:")
    print(f"Activity: {activity_found}")
    print(f"Observed elements: {element_count}")
    print(f"Fingerprint: {initial_fingerprint}")

    # 6. Build semantic understanding & ReasoningContext
    understanding = analyze_screen(initial_api_state)
    context = build_reasoning_context(
        screen_data=initial_api_state,
        understanding=understanding,
        screen_id=initial_fingerprint,
        exploration_step=1,
    )

    # 7. Initialize GeminiLLMClient & LLMReasoner
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    try:
        gemini_client = GeminiLLMClient(model_name=model_name)
        reasoner = LLMReasoner(client=gemini_client)
    except Exception as exc:
        print(f"\n[ERROR] Failed to initialize Gemini model '{model_name}': {exc}")
        return 1

    # 8. Request action decision from Gemini
    try:
        decision = reasoner.decide(context)
    except Exception as exc:
        print(f"\n[ERROR] Exception during reasoning step: {exc}")
        return 1

    target_id = decision.target.element_id if decision.target else None
    print("\nGemini decision:")
    print(f"Action: {decision.action}")
    print(f"Target: {target_id or 'None'}")
    print(f"Reason: {decision.reason or 'None'}")

    # 9. Safety validation
    safety_validator = SafetyValidator()
    val_result = safety_validator.validate_action(decision, context)

    if not val_result.allowed:
        print("\nSafety validation:")
        print(f"REJECTED ({val_result.reason})")
        print("\nAction aborted for safety.")
        return 1

    if decision.action not in ALLOWED_SMOKE_ACTIONS:
        print("\nSafety validation:")
        print(f"REJECTED (Action '{decision.action}' not in allowed exploration actions)")
        print("\nAction aborted for safety.")
        return 1

    print("\nSafety validation:")
    print("PASS")

    # 10. Execute the action through AndroidController
    print("\nExecuting action...")
    action_dict = decision.to_dict()
    ctrl_action = to_controller_action(action_dict)

    action_succeeded = False
    try:
        new_raw_state = controller.execute_action(ctrl_action)
        action_succeeded = True
    except Exception as exc:
        print(f"Execution error: {exc}")
        new_raw_state = controller.get_current_state()

    print("\nAction result:")
    print("SUCCESS" if action_succeeded else "FAILURE")

    # 11. Screen change detection
    new_api_state = to_api_screen_state(new_raw_state)
    new_fingerprint = compute_screen_fingerprint(new_api_state)
    screen_changed = initial_fingerprint != new_fingerprint

    print("\nScreen changed:")
    print("YES" if screen_changed else "NO")

    print("\n==================================================")
    return 0 if action_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
