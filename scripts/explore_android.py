"""
Multi-Step Autonomous Android App Exploration Runner.

Connects the real Gemini LLM reasoning backend to a running Android emulator/device
to autonomously explore an application using the full observe-understand-decide-act loop.
"""

import os
import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root and android-controller are in sys.path
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

from agent.agent import ExplorationAgent
from agent.gemini_client import DEFAULT_GEMINI_MODEL, GeminiLLMClient, resolve_gemini_api_key
from agent.llm_reasoner import LLMReasoner
from agent.memory import ExplorationMemory
from agent.safety import SafetyValidator
from controller import AndroidController
from integration.explorer import AutonomousExplorer


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

    # 3. Parse ZERO_TOUCH_MAX_STEPS (default: 10)
    raw_max_steps = os.environ.get("ZERO_TOUCH_MAX_STEPS", "10")
    try:
        max_steps = int(raw_max_steps)
        if max_steps <= 0:
            max_steps = 10
    except ValueError:
        max_steps = 10

    print("==================================================")
    print("AUTONOMOUS EXPLORATION STARTING")
    print("==================================================")
    print(f"Device: {target_device}")
    print(f"App: {package_name}")
    print(f"Max steps: {max_steps}")

    # 4. Connect to Android Controller
    try:
        controller = AndroidController()
        connected_id = controller.connect(device_id=target_device)
    except Exception as exc:
        print(f"\n[ERROR] Failed to connect to Android device '{target_device}': {exc}")
        return 1

    # 5. Launch the target app
    try:
        controller.launch_app(package_name, activity_name=activity_name)
    except Exception as exc:
        print(f"\n[ERROR] Failed to launch application '{package_name}': {exc}")
        return 1

    # 6. Initialize Agent with Gemini LLMReasoner, Memory, and SafetyValidator
    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    try:
        gemini_client = GeminiLLMClient(model_name=model_name)
        safety_validator = SafetyValidator()
        reasoner = LLMReasoner(client=gemini_client, safety_validator=safety_validator)
        memory = ExplorationMemory()
        agent = ExplorationAgent(
            reasoner=reasoner,
            memory=memory,
            safety_validator=safety_validator,
        )
    except Exception as exc:
        print(f"\n[ERROR] Failed to initialize AI model or agent: {exc}")
        return 1

    # 7. Run Autonomous Exploration Loop
    explorer = AutonomousExplorer(
        controller=controller,
        agent=agent,
        max_steps=max_steps,
        package_name=package_name,
        verbose=True,
    )

    try:
        summary = explorer.run()
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Autonomous exploration encountered unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
