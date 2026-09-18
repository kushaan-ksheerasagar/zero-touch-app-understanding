"""Integration verification test for ZeroTouch Demo App screens.

Tests observation, UI parsing, and action execution across all 6 application screens:
1. LoginActivity
2. HomeActivity
3. SearchActivity
4. ResultsActivity
5. ProductActivity
6. ProfileActivity
"""

import os
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple, Union

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adb_client import ADBClient, CommandRunner
from controller import AndroidController
from ui_parser import parse_ui_hierarchy


LOGIN_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.zerotouch.demo" bounds="[0,0][1080,2400]">
    <node index="0" text="ZeroTouch Demo" resource-id="com.zerotouch.demo:id/text_login_title" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[100,200][980,300]" />
    <node index="1" text="" resource-id="com.zerotouch.demo:id/input_email" class="android.widget.EditText" package="com.zerotouch.demo" bounds="[100,450][980,580]" clickable="true" focusable="true" enabled="true" password="false" />
    <node index="2" text="" resource-id="com.zerotouch.demo:id/input_password" class="android.widget.EditText" package="com.zerotouch.demo" bounds="[100,620][980,750]" clickable="true" focusable="true" enabled="true" password="true" />
    <node index="3" text="Sign In" resource-id="com.zerotouch.demo:id/btn_login" class="android.widget.Button" package="com.zerotouch.demo" bounds="[100,800][980,930]" clickable="true" focusable="true" enabled="true" />
  </node>
</hierarchy>"""

HOME_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.zerotouch.demo" bounds="[0,0][1080,2400]">
    <node index="0" text="Welcome back, Alex!" resource-id="com.zerotouch.demo:id/text_home_welcome" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,150][800,230]" />
    <node index="1" text="" content-desc="Profile" resource-id="com.zerotouch.demo:id/btn_profile" class="android.widget.ImageView" package="com.zerotouch.demo" bounds="[900,150][1000,250]" clickable="true" enabled="true" />
    <node index="2" text="Search electronics, audio..." resource-id="com.zerotouch.demo:id/btn_search" class="android.widget.Button" package="com.zerotouch.demo" bounds="[50,260][1030,380]" clickable="true" enabled="true" />
    <node index="3" text="" resource-id="com.zerotouch.demo:id/home_scroll" class="android.widget.ScrollView" package="com.zerotouch.demo" bounds="[0,400][1080,2300]" scrollable="true">
      <node index="0" text="Wireless Noise Cancelling Headphones" resource-id="com.zerotouch.demo:id/card_product_1" class="android.widget.LinearLayout" package="com.zerotouch.demo" bounds="[50,450][1030,750]" clickable="true" enabled="true" />
      <node index="1" text="Smart Watch Series 7" resource-id="com.zerotouch.demo:id/card_product_2" class="android.widget.LinearLayout" package="com.zerotouch.demo" bounds="[50,800][1030,1100]" clickable="true" enabled="true" />
    </node>
  </node>
</hierarchy>"""

SEARCH_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.zerotouch.demo" bounds="[0,0][1080,2400]">
    <node index="0" text="Back" resource-id="com.zerotouch.demo:id/btn_back" class="android.widget.ImageView" package="com.zerotouch.demo" bounds="[30,120][120,210]" clickable="true" enabled="true" />
    <node index="1" text="" resource-id="com.zerotouch.demo:id/input_search" class="android.widget.EditText" package="com.zerotouch.demo" bounds="[150,120][880,210]" clickable="true" focusable="true" enabled="true" password="false" />
    <node index="2" text="Go" resource-id="com.zerotouch.demo:id/btn_do_search" class="android.widget.Button" package="com.zerotouch.demo" bounds="[900,120][1040,210]" clickable="true" enabled="true" />
    <node index="3" text="Headphones" resource-id="com.zerotouch.demo:id/chip_headphones" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,250][250,320]" clickable="true" enabled="true" />
  </node>
</hierarchy>"""

RESULTS_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.zerotouch.demo" bounds="[0,0][1080,2400]">
    <node index="0" text="Back" resource-id="com.zerotouch.demo:id/btn_back" class="android.widget.ImageView" package="com.zerotouch.demo" bounds="[30,120][120,210]" clickable="true" enabled="true" />
    <node index="1" text="Results for 'Noise Cancelling'" resource-id="com.zerotouch.demo:id/text_results_title" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[150,130][900,200]" />
    <node index="2" text="" resource-id="com.zerotouch.demo:id/results_scroll" class="android.widget.ScrollView" package="com.zerotouch.demo" bounds="[0,230][1080,2300]" scrollable="true">
      <node index="0" text="Sony WH-1000XM5" resource-id="com.zerotouch.demo:id/result_card_1" class="android.widget.LinearLayout" package="com.zerotouch.demo" bounds="[50,260][1030,550]" clickable="true" enabled="true" />
      <node index="1" text="Bose QuietComfort 45" resource-id="com.zerotouch.demo:id/result_card_2" class="android.widget.LinearLayout" package="com.zerotouch.demo" bounds="[50,600][1030,890]" clickable="true" enabled="true" />
    </node>
  </node>
</hierarchy>"""

PRODUCT_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.zerotouch.demo" bounds="[0,0][1080,2400]">
    <node index="0" text="Back" resource-id="com.zerotouch.demo:id/btn_back" class="android.widget.ImageView" package="com.zerotouch.demo" bounds="[30,120][120,210]" clickable="true" enabled="true" />
    <node index="1" text="Sony WH-1000XM5" resource-id="com.zerotouch.demo:id/text_product_name" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,750][900,830]" />
    <node index="2" text="$399.99" resource-id="com.zerotouch.demo:id/text_product_price" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,850][300,920]" />
    <node index="3" text="Industry Leading Noise Canceling with two processors and 8 microphones." resource-id="com.zerotouch.demo:id/text_product_description" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,950][1030,1150]" />
  </node>
</hierarchy>"""

PROFILE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.zerotouch.demo" bounds="[0,0][1080,2400]">
    <node index="0" text="Back" resource-id="com.zerotouch.demo:id/btn_back" class="android.widget.ImageView" package="com.zerotouch.demo" bounds="[30,120][120,210]" clickable="true" enabled="true" />
    <node index="1" text="Alex Mercer" resource-id="com.zerotouch.demo:id/text_user_name" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,250][600,320]" />
    <node index="2" text="alex.mercer@example.com" resource-id="com.zerotouch.demo:id/text_user_email" class="android.widget.TextView" package="com.zerotouch.demo" bounds="[50,330][700,390]" />
    <node index="3" text="Account Details" resource-id="com.zerotouch.demo:id/row_account" class="android.widget.LinearLayout" package="com.zerotouch.demo" bounds="[50,450][1030,550]" clickable="true" enabled="true" />
    <node index="4" text="Notifications" resource-id="com.zerotouch.demo:id/row_notifications" class="android.widget.LinearLayout" package="com.zerotouch.demo" bounds="[50,570][1030,670]" clickable="true" enabled="true" />
  </node>
</hierarchy>"""


class DemoAppMockRunner(CommandRunner):
    """Simulates Android device responses transitioning through the 6 Demo App screens."""

    def __init__(self) -> None:
        self.executed_commands: List[List[str]] = []
        self.current_screen_xml = LOGIN_XML
        self.current_screen_activity = "com.zerotouch.demo/.LoginActivity"
        self.navigation_stack: List[Tuple[str, str]] = []

    def set_screen(self, xml: str, activity: str) -> None:
        self.current_screen_xml = xml
        self.current_screen_activity = activity

    def run(
        self,
        cmd: List[str],
        timeout: float = 10.0,
        binary: bool = False,
    ) -> Tuple[Union[str, bytes], str, int]:
        self.executed_commands.append(cmd)

        if cmd[-1] == "devices":
            return "List of devices attached\nemulator-5554\tdevice\n", "", 0

        if any("screencap" in arg for arg in cmd) and binary:
            return b"\x89PNG\r\n\x1a\ndemo_screen_bytes", "", 0

        if any("cat" in arg for arg in cmd) and any("window_dump.xml" in arg for arg in cmd):
            return self.current_screen_xml, "", 0

        if any("window" in arg for arg in cmd):
            return f"  mCurrentFocus=Window{{abc u0 {self.current_screen_activity}}}\n", "", 0

        if any("activities" in arg for arg in cmd):
            return f"mResumedActivity: ActivityRecord{{def u0 {self.current_screen_activity} t1}}\n", "", 0

        # Simulate transitions when buttons are tapped
        if "input" in cmd and "tap" in cmd:
            tap_x, tap_y = int(cmd[-2]), int(cmd[-1])
            # Check Login -> Home (btn_login: [100,800][980,930], center=(540, 865))
            if "LoginActivity" in self.current_screen_activity and 800 <= tap_y <= 930:
                self.navigation_stack.append((self.current_screen_xml, self.current_screen_activity))
                self.set_screen(HOME_XML, "com.zerotouch.demo/.HomeActivity")

            # Check Home -> Search (btn_search: [50,260][1030,380], center=(540, 320))
            elif "HomeActivity" in self.current_screen_activity and 260 <= tap_y <= 380:
                self.navigation_stack.append((self.current_screen_xml, self.current_screen_activity))
                self.set_screen(SEARCH_XML, "com.zerotouch.demo/.SearchActivity")

            # Check Home -> Profile (btn_profile: [900,150][1000,250], center=(950, 200))
            elif "HomeActivity" in self.current_screen_activity and 900 <= tap_x <= 1000 and 150 <= tap_y <= 250:
                self.navigation_stack.append((self.current_screen_xml, self.current_screen_activity))
                self.set_screen(PROFILE_XML, "com.zerotouch.demo/.ProfileActivity")

            # Check Search -> Results (btn_do_search: [900,120][1040,210], center=(970, 165))
            elif "SearchActivity" in self.current_screen_activity and 900 <= tap_x <= 1040 and 120 <= tap_y <= 210:
                self.navigation_stack.append((self.current_screen_xml, self.current_screen_activity))
                self.set_screen(RESULTS_XML, "com.zerotouch.demo/.ResultsActivity")

            # Check Results -> Product (result_card_1: [50,260][1030,550], center=(540, 405))
            elif "ResultsActivity" in self.current_screen_activity and 260 <= tap_y <= 550:
                self.navigation_stack.append((self.current_screen_xml, self.current_screen_activity))
                self.set_screen(PRODUCT_XML, "com.zerotouch.demo/.ProductActivity")

        # Simulate Back button
        if "input" in cmd and "keyevent" in cmd and cmd[-1] == "4":
            if self.navigation_stack:
                prev_xml, prev_act = self.navigation_stack.pop()
                self.set_screen(prev_xml, prev_act)

        return "", "", 0


class TestDemoAppScreens(unittest.TestCase):
    """Verifies the complete ZeroTouch Demo App 6-screen navigation flow."""

    def setUp(self) -> None:
        self.runner = DemoAppMockRunner()
        self.adb = ADBClient(runner=self.runner)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.controller = AndroidController(
            adb_client=self.adb,
            screenshot_dir=self.tmp_dir.name,
            stabilization_delay=0.001,
        )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_complete_6_screen_demo_app_flow(self) -> None:
        # Connect to device
        device_id = self.controller.connect()
        self.assertEqual(device_id, "emulator-5554")

        # 1. Observe Login Screen
        s1 = self.controller.get_current_state()
        self.assertEqual(s1["current_package"], "com.zerotouch.demo")
        self.assertIn("LoginActivity", s1["current_activity"])

        email_elem = next(e for e in s1["elements"] if e["element_id"] == "com.zerotouch.demo:id/input_email")
        pw_elem = next(e for e in s1["elements"] if e["element_id"] == "com.zerotouch.demo:id/input_password")
        login_btn = next(e for e in s1["elements"] if e["element_id"] == "com.zerotouch.demo:id/btn_login")

        self.assertEqual(email_elem["input_type"], "text")
        self.assertEqual(pw_elem["input_type"], "password")
        self.assertTrue(login_btn["clickable"])

        # Type credentials and click Sign In
        self.controller.execute_action({
            "action": "type",
            "target": {"element_id": "com.zerotouch.demo:id/input_email"},
            "text": "alex.mercer@example.com",
        })
        self.controller.execute_action({
            "action": "type",
            "target": {"element_id": "com.zerotouch.demo:id/input_password"},
            "text": "demo_password",
        })
        s2 = self.controller.execute_action({
            "action": "tap",
            "target": {"element_id": "com.zerotouch.demo:id/btn_login"},
        })

        # 2. Observe Home Screen
        self.assertIn("HomeActivity", s2["current_activity"])
        welcome = next(e for e in s2["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_home_welcome")
        self.assertIn("Welcome back, Alex!", welcome["text"])

        scroll_home = next(e for e in s2["elements"] if e["element_id"] == "com.zerotouch.demo:id/home_scroll")
        self.assertTrue(scroll_home["scrollable"])

        # Test scroll on Home
        self.controller.execute_action({"action": "scroll", "direction": "down"})

        # Tap Search button -> SearchActivity
        s3 = self.controller.execute_action({
            "action": "tap",
            "target": {"element_id": "com.zerotouch.demo:id/btn_search"},
        })

        # 3. Observe Search Screen
        self.assertIn("SearchActivity", s3["current_activity"])
        search_input = next(e for e in s3["elements"] if e["element_id"] == "com.zerotouch.demo:id/input_search")
        do_search_btn = next(e for e in s3["elements"] if e["element_id"] == "com.zerotouch.demo:id/btn_do_search")
        chip = next(e for e in s3["elements"] if e["element_id"] == "com.zerotouch.demo:id/chip_headphones")

        self.assertEqual(search_input["type"], "android.widget.EditText")
        self.assertTrue(do_search_btn["clickable"])
        self.assertTrue(chip["clickable"])

        # Type search query with hide_keyboard
        self.controller.execute_action({
            "action": "type",
            "target": {"element_id": "com.zerotouch.demo:id/input_search"},
            "text": "Noise Cancelling",
            "hide_keyboard": True,
        })

        # Tap Go -> ResultsActivity
        s4 = self.controller.execute_action({
            "action": "tap",
            "target": {"element_id": "com.zerotouch.demo:id/btn_do_search"},
        })

        # 4. Observe Results Screen
        self.assertIn("ResultsActivity", s4["current_activity"])
        title_elem = next(e for e in s4["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_results_title")
        self.assertIn("Noise Cancelling", title_elem["text"])

        res_card1 = next(e for e in s4["elements"] if e["element_id"] == "com.zerotouch.demo:id/result_card_1")
        res_scroll = next(e for e in s4["elements"] if e["element_id"] == "com.zerotouch.demo:id/results_scroll")
        self.assertTrue(res_scroll["scrollable"])
        self.assertTrue(res_card1["clickable"])

        # Scroll on results
        self.controller.execute_action({"action": "scroll", "direction": "down"})

        # Tap Result Card 1 -> ProductActivity
        s5 = self.controller.execute_action({
            "action": "tap",
            "target": {"element_id": "com.zerotouch.demo:id/result_card_1"},
        })

        # 5. Observe Product Screen
        self.assertIn("ProductActivity", s5["current_activity"])
        prod_name = next(e for e in s5["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_product_name")
        prod_price = next(e for e in s5["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_product_price")
        prod_desc = next(e for e in s5["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_product_description")

        self.assertEqual(prod_name["text"], "Sony WH-1000XM5")
        self.assertEqual(prod_price["text"], "$399.99")
        self.assertIn("Noise Canceling", prod_desc["text"])

        # Test Back Navigation: Product -> Results -> Search -> Home
        back1 = self.controller.execute_action({"action": "back"})
        self.assertIn("ResultsActivity", back1["current_activity"])

        back2 = self.controller.execute_action({"action": "back"})
        self.assertIn("SearchActivity", back2["current_activity"])

        back3 = self.controller.execute_action({"action": "back"})
        self.assertIn("HomeActivity", back3["current_activity"])

        # 6. Observe Profile Screen: Home -> Profile
        s6 = self.controller.execute_action({
            "action": "tap",
            "target": {"element_id": "com.zerotouch.demo:id/btn_profile"},
        })
        self.assertIn("ProfileActivity", s6["current_activity"])

        user_name = next(e for e in s6["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_user_name")
        user_email = next(e for e in s6["elements"] if e["element_id"] == "com.zerotouch.demo:id/text_user_email")
        row_account = next(e for e in s6["elements"] if e["element_id"] == "com.zerotouch.demo:id/row_account")
        row_notif = next(e for e in s6["elements"] if e["element_id"] == "com.zerotouch.demo:id/row_notifications")

        self.assertEqual(user_name["text"], "Alex Mercer")
        self.assertEqual(user_email["text"], "alex.mercer@example.com")
        self.assertTrue(row_account["clickable"])
        self.assertTrue(row_notif["clickable"])

        # Return from Profile to Home
        back_final = self.controller.execute_action({"action": "back"})
        self.assertIn("HomeActivity", back_final["current_activity"])


if __name__ == "__main__":
    unittest.main()
