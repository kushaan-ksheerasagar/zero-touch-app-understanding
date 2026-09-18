"""
Real-device smoke test script for Zero-Touch App Understanding.

Performs one real Controller -> Agent -> Controller cycle on a connected
Android device or emulator using the Phase 2 IntegrationRunner.
"""

import os
import sys

# 1. Add project root and android-controller to sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
ANDROID_CONTROLLER_DIR = os.path.join(PROJECT_ROOT, "android-controller")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if ANDROID_CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, ANDROID_CONTROLLER_DIR)

from controller import AndroidController
from adb_client import ADBError, DeviceNotFoundError, ADBTimeoutError
from agent.agent import ExplorationAgent
from integration.runner import IntegrationRunner


def main() -> int:
    print("==================================================")
    print("Zero-Touch App Understanding - Real Device Smoke Test")
    print("==================================================")

    try:
        # 3. Create controller
        controller = AndroidController()

        # 4. Connect to available emulator/device
        print("Connecting to Android device/emulator...")
        device_id = controller.connect()
        print(f"Connected to device: {device_id}")

        # 5. Launch Android Settings
        print("Launching Android Settings (com.android.settings)...")
        initial_state = controller.launch_app("com.android.settings")
        print(f"App launched. Initial Activity: {initial_state.get('current_activity', 'unknown')}")

        # 6. Create agent
        agent = ExplorationAgent()

        # 7. Create runner
        runner = IntegrationRunner(controller=controller, agent=agent)

        # 8. Execute exactly ONE cycle
        print("Executing Controller -> Agent -> Controller cycle...")
        result = runner.run_cycle()

        # 9. Print readable report
        state = result.get("state", {})
        action_executed = result.get("action_executed", {})
        elements = state.get("elements", [])

        print("\n==================================================")
        print("SMOKE TEST REPORT")
        print("==================================================")
        print(f"Connected Device ID: {device_id}")
        print(f"Action Selected:     {action_executed.get('action')} (target: {action_executed.get('element_id', 'none')})")
        print(f"Cycle Success:       {result.get('success')}")
        if result.get("error"):
            print(f"Error Details:       {result.get('error')}")
        print(f"Resulting Activity:  {state.get('current_activity', 'N/A')}")
        print(f"Observed Elements:   {len(elements)}")
        print(f"Screenshot Path:     {state.get('screenshot_path', 'N/A')}")
        print("==================================================")

        return 0 if result.get("success") else 1

    except DeviceNotFoundError as exc:
        print(f"\n[ERROR] No active Android device found: {exc}")
        print("Please ensure an emulator is running or a device is connected via USB with USB debugging enabled.")
        return 2
    except ADBTimeoutError as exc:
        print(f"\n[ERROR] ADB command timed out: {exc}")
        return 3
    except ADBError as exc:
        print(f"\n[ERROR] ADB execution error: {exc}")
        return 4
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error during smoke test: {exc}")
        return 5


if __name__ == "__main__":
    sys.exit(main())
