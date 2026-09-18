# Android Controller Module (Phase 1 & 2)

The **Android Controller** is the "eyes and hands" module of the **Zero-Touch App Understanding** system. It connects to an Android emulator or physical device over ADB, launches applications, captures screenshots, dumps and parses the UIAutomator hierarchy into structured JSON, and executes mechanical UI actions.

> [!NOTE]
> This module contains **no AI or decision-making logic**. It purely executes actions requested by the Agent and returns the updated screen state.

---

## Architecture

```
android-controller/
├── __init__.py           # Package exports (AndroidController, ADBClient, UIParser, errors)
├── adb_client.py         # Isolated low-level wrapper around ADB CLI commands
├── ui_parser.py          # UIAutomator XML hierarchy parser and element extractor
├── controller.py         # High-level facade (connect, launch_app, get_current_state, execute_action)
├── tests/                # Comprehensive unit tests (mocked ADB runner, runs offline)
│   ├── fixtures/         # Sample UIAutomator XML fixtures
│   ├── test_adb_client.py
│   ├── test_ui_parser.py
│   ├── test_controller.py
│   └── test_demo_app_integration.py
└── README.md
```

---

## Key Features & Reliability Guarantees

1. **Robust Device Discovery**:
   - Auto-discovers connected devices; prefers `emulator-5554` when multiple devices are connected.
   - Respects `ANDROID_DEVICE_ID` environment variable if specified.
   - Discovers `adb` in `PATH`, `ADB_PATH`, `ANDROID_HOME`, or `ANDROID_SDK_ROOT`.
   - Clear diagnostic errors (`DeviceNotFoundError`, `ADBTimeoutError`) when devices are missing, offline, or unauthorized.

2. **Collision-Free Deterministic Element IDs**:
   - Elements with unique resource IDs retain their natural identifier (e.g. `com.example.zeroapp:id/login_button`).
   - Duplicate resource IDs (e.g. repeated list items or product cards) are deterministically indexed (e.g. `com.example:id/card_0`, `com.example:id/card_1`), guaranteeing no collisions.
   - Elements without resource IDs receive stable fallback IDs based on class and document tree position (e.g. `elem_4_textview`).
   - Full attribute extraction: `resource_id`, `class_name`, `type`, `text`, `content_description`, `bounds`, `center`, `clickable`, `scrollable`, `focusable`, `enabled`, `password`, `input_type`, and `package`.

3. **System UI Isolation**:
   - Automatically filters out Android system UI components (`com.android.systemui` status bar, navigation bar, virtual keyboard overlays) so autonomous agents do not accidentally interact outside the application.

4. **Container-Aware Scrolling**:
   - Scroll actions automatically compute swipe vectors within the bounds of target scroll containers or on-screen `scrollable` views rather than blind full-screen swipes.

5. **Keyboard & IME Handling**:
   - Automatically taps target input fields to establish focus before typing.
   - Robust character escaping for Android shell input text (`%s` for spaces, escaping quotes, ampersands, semicolons, and shell metacharacters).
   - Supports `hide_keyboard: true` (via `KEYCODE_ESCAPE = 111`) to dismiss the soft keyboard without triggering backward navigation.

---

## Usage Example

```python
from controller import AndroidController

# Initialize controller (optionally specify custom screenshot_dir or device_id)
controller = AndroidController(screenshot_dir="screenshots")

# 1. Connect to emulator or device
device_id = controller.connect()
print(f"Connected to device: {device_id}")

# 2. Launch target app and get initial state
state = controller.launch_app("com.zerotouch.demo", ".LoginActivity")
print(f"Current Package: {state['current_package']}")
print(f"Current Activity: {state['current_activity']}")
print(f"Discovered {len(state['elements'])} UI elements.")

# 3. Tap by element_id
state = controller.execute_action({
    "action": "tap",
    "target": {
        "element_id": "com.zerotouch.demo:id/btn_login"
    }
})

# 4. Tap by screen coordinates list
state = controller.execute_action({
    "action": "tap",
    "target": {
        "coordinates": [540, 960]
    }
})

# 5. Type text with focus and keyboard dismissal
state = controller.execute_action({
    "action": "type",
    "target": {
        "element_id": "com.zerotouch.demo:id/input_search"
    },
    "text": "Noise Cancelling",
    "hide_keyboard": True
})

# 6. Scroll (down, up, left, right) inside a specific container
state = controller.execute_action({
    "action": "scroll",
    "direction": "down",
    "target": {
        "element_id": "com.zerotouch.demo:id/results_scroll"
    }
})

# 7. Press Back
state = controller.execute_action({
    "action": "back"
})

# 8. Wait
state = controller.execute_action({
    "action": "wait",
    "duration": 1.5
})
```

---

## Data Schemas

### Screen State Schema (`get_current_state()`)

```json
{
  "screenshot_path": "screenshots/screen_0001.png",
  "current_activity": "com.zerotouch.demo/.LoginActivity",
  "current_package": "com.zerotouch.demo",
  "elements": [
    {
      "element_id": "com.zerotouch.demo:id/btn_login",
      "resource_id": "com.zerotouch.demo:id/btn_login",
      "class_name": "android.widget.Button",
      "type": "android.widget.Button",
      "text": "Sign In",
      "content_description": "",
      "clickable": true,
      "scrollable": false,
      "focusable": true,
      "enabled": true,
      "bounds": [100, 800, 980, 930],
      "center": [540, 865],
      "package": "com.zerotouch.demo",
      "password": false,
      "input_type": ""
    }
  ]
}
```

### Action Payloads (`execute_action()`)

| Action | Payload Example | Description |
|---|---|---|
| **tap (element)** | `{"action": "tap", "target": {"element_id": "com.example:id/btn"}}` | Taps center of target element |
| **tap (coords)** | `{"action": "tap", "target": {"coordinates": [540, 960]}}` | Taps exact pixel coordinates |
| **type** | `{"action": "type", "text": "hello", "target": {"element_id": "..."}, "hide_keyboard": true}` | Focuses input, types text, dismisses keyboard |
| **scroll** | `{"action": "scroll", "direction": "down", "target": {"element_id": "..."}}` | Scrolls container in specified direction |
| **swipe** | `{"action": "swipe", "x1": 100, "y1": 500, "x2": 100, "y2": 200, "duration_ms": 300}` | Executes custom swipe gesture |
| **back** | `{"action": "back"}` | Injects KEYCODE_BACK (4) |
| **wait** | `{"action": "wait", "duration": 1.5}` | Stabilizes and pauses for seconds or `duration_ms` |

---

## Running Unit Tests

The test suite uses a mock command runner and does **not** require a running Android emulator or physical device:

```bash
python3 -m unittest discover -s android-controller/tests -v
```
