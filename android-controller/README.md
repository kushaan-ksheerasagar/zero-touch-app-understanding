# Android Controller (Phase 1)

The **Android Controller** is the "eyes and hands" of the **zero-touch-app-understanding** system. It manages low-level communication with Android devices and emulators, extracts visual and structural state, and performs actions (tap, scroll, type, back, wait).

---

## 1. Prerequisites

- **Python 3.8+** (Built and verified on Python 3.12)
- **Android SDK Platform-Tools** (including `adb`) installed and accessible via system `PATH`, or configured via custom path.
- An active **Android Emulator** (e.g. Android Studio AVD) or a physical Android device with USB debugging enabled.

---

## 2. ADB Setup

### Checking ADB Installation

Verify ADB is installed and accessible from your terminal:

```bash
adb version
```

If ADB is not recognized, add the Android SDK `platform-tools` directory to your system environment variables:
- **Windows**: `C:\Users\<Username>\AppData\Local\Android\Sdk\platform-tools`
- **macOS / Linux**: `~/Library/Android/sdk/platform-tools` or `/usr/lib/android-sdk/platform-tools`

### Connecting an Emulator or Physical Device

1. **Start an Android Emulator**:
   - In Android Studio: Open **Device Manager** -> click **Play** next to an AVD.
   - Command line:
     ```bash
     emulator -avd <avd_name>
     ```
2. **Physical Device**:
   - Enable **Developer Options** (tap *Settings -> About Phone -> Build Number* 7 times).
   - In Developer Options, enable **USB Debugging**.
   - Connect the device via USB and accept the debugging authorization prompt on the device screen.
3. **Verify Connected Devices**:
   ```bash
   adb devices
   ```
   You should see:
   ```text
   List of devices attached
   emulator-5554    device
   ```

---

## 3. Module Architecture

```text
android-controller/
├── __init__.py           # Package exports (AndroidController, ADBClient, UIParser)
├── adb_client.py         # Subprocess-based ADB command wrapper with error handling
├── ui_parser.py          # UIAutomator XML parser, bounds parser, filtering, and element ID fallback
├── controller.py         # Facade coordinating state observation and action execution
├── sample_dump.xml       # Realistic UI hierarchy fixture for testing
├── tests/                # Complete unit test suite (mocked, no real device required)
│   ├── __init__.py
│   ├── test_adb_client.py
│   ├── test_ui_parser.py
│   └── test_controller.py
└── README.md
```

### Components

1. **`adb_client.py`**:
   - Encapsulates all ADB commands via Python `subprocess`.
   - Methods: `list_devices()`, `launch_app()`, `screenshot()`, `dump_ui_hierarchy()`, `get_current_activity()`, `tap()`, `swipe()`, `type_text()`, `press_back()`.
   - Strong error handling with custom exceptions: `ADBError`, `ADBTimeoutError`, and `DeviceNotFoundError`.
2. **`ui_parser.py`**:
   - Converts UIAutomator XML output into standardized Python element dictionaries.
   - Converts `"[x1,y1][x2,y2]"` into coordinate arrays and computes center `[x, y]`.
   - Generates deterministic fallback element IDs (`elem_{index}_{class}_{x1}_{y1}`) when `resource-id` is empty.
   - Filters out non-interactive layout containers while strictly preserving all actionable or labeled UI elements.
3. **`controller.py`**:
   - Provides `AndroidController`, the unified interface for the system.
   - Exposes:
     - `connect(device_id=None)`: Connects to a target or first available active device.
     - `launch_app(package_name, activity_name=None)`: Starts an app and returns initial screen state.
     - `get_current_state()`: Captures screenshot, records current activity, parses UI elements.
     - `execute_action(action_dict)`: Resolves targets, executes interaction, stabilizes, and returns updated screen state.

---

## 4. Running Tests

The test suite runs with Python's built-in `unittest` framework and uses mocked ADB subprocess responses. **No connected device is required to run tests.**

Run all unit tests from the workspace root:

```bash
python -m unittest discover -s android-controller/tests -v
```

Expected output:
```text
Ran 42 tests in ~0.5s
OK
```

---

## 5. Usage Example

```python
import sys
import os

# Add android-controller to Python path if necessary
sys.path.insert(0, os.path.abspath("android-controller"))

from controller import AndroidController

# 1. Initialize controller
controller = AndroidController(output_dir="artifacts/controller", stabilization_time=1.0)

# 2. Connect to an available emulator or device
device_id = controller.connect()
print(f"Connected to device: {device_id}")

# 3. Launch an app
state = controller.launch_app("com.example.shop", ".MainActivity")
print(f"Current Activity: {state['current_activity']}")
print(f"Screenshot saved to: {state['screenshot_path']}")
print(f"Found {len(state['elements'])} UI elements.")

# 4. Inspect an element
for elem in state["elements"]:
    if elem["clickable"]:
        print(f"Clickable: {elem['element_id']} -> Center: {elem['center']}")

# 5. Execute Actions

# Tap an element by ID
new_state = controller.execute_action({
    "action": "tap",
    "target": {"element_id": "com.example.shop:id/btn_signin"}
})

# Type into a text field
new_state = controller.execute_action({
    "action": "type",
    "text": "alice@example.com",
    "target": {"element_id": "com.example.shop:id/input_email"}
})

# Scroll down
new_state = controller.execute_action({
    "action": "scroll",
    "direction": "down"
})

# Press Back
new_state = controller.execute_action({
    "action": "back"
})

# Wait for animations or network
new_state = controller.execute_action({
    "action": "wait",
    "duration": 2.0
})
```

---

## 6. Output Data Format

### Screen State Schema (`get_current_state()`)

```json
{
  "screenshot_path": "artifacts/controller/screenshots/screen_001.png",
  "current_activity": "com.example.shop/.MainActivity",
  "elements": [
    {
      "element_id": "com.example.shop:id/btn_search",
      "type": "android.widget.ImageButton",
      "text": "",
      "content_description": "Search Store",
      "bounds": [940, 90, 1040, 190],
      "center": [990, 140],
      "clickable": true,
      "scrollable": false,
      "focusable": true,
      "enabled": true
    }
  ]
}
```
