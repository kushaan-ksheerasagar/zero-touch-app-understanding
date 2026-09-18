"""Unit tests for ui_parser."""

import os
import unittest

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui_parser import (
    UIParser,
    calculate_center,
    compute_center,
    is_useful_element,
    parse_bounds,
    parse_ui_hierarchy,
)


class TestUIParser(unittest.TestCase):

    def setUp(self) -> None:
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        self.sample_xml_path = os.path.join(self.fixtures_dir, "sample_dump.xml")
        with open(self.sample_xml_path, "r", encoding="utf-8") as f:
            self.sample_xml = f.read()

    def test_parse_bounds_valid(self) -> None:
        bounds = parse_bounds("[100,200][980,350]")
        self.assertEqual(bounds, [100, 200, 980, 350])

    def test_parse_bounds_invalid_or_empty(self) -> None:
        self.assertIsNone(parse_bounds(""))
        self.assertIsNone(parse_bounds("invalid_bounds"))
        self.assertIsNone(parse_bounds("[100,200]"))
        self.assertIsNone(parse_bounds(None))  # type: ignore

    def test_parse_bounds_negative_coordinates(self) -> None:
        bounds = parse_bounds("[-50,-100][500,800]")
        self.assertEqual(bounds, [-50, -100, 500, 800])

    def test_calculate_center(self) -> None:
        center = calculate_center([100, 200, 980, 350])
        # (100 + 980) // 2 = 540, (200 + 350) // 2 = 275
        self.assertEqual(center, [540, 275])
        self.assertEqual(compute_center([100, 200, 980, 350]), [540, 275])

    def test_calculate_center_empty(self) -> None:
        self.assertEqual(calculate_center([]), [0, 0])

    def test_parse_ui_hierarchy_with_filter(self) -> None:
        elements = parse_ui_hierarchy(self.sample_xml, filter_useful=True)
        # Should filter out empty FrameLayout and LinearLayout, keeping:
        # 1. title_text (TextView with text)
        # 2. username_input (EditText, clickable/focusable)
        # 3. password_input (EditText, clickable/focusable)
        # 4. login_button (Button, clickable)
        # 5. Forgot Password (TextView, clickable)
        # 6. scroll_container (ScrollView, scrollable)
        # 7. terms_text (TextView with text)
        self.assertEqual(len(elements), 7)

        # Check button
        login_btn = next((e for e in elements if e["element_id"] == "com.example.zeroapp:id/login_button"), None)
        self.assertIsNotNone(login_btn)
        self.assertEqual(login_btn["type"], "android.widget.Button")
        self.assertEqual(login_btn["class_name"], "android.widget.Button")
        self.assertEqual(login_btn["resource_id"], "com.example.zeroapp:id/login_button")
        self.assertEqual(login_btn["text"], "Sign In")
        self.assertTrue(login_btn["clickable"])
        self.assertTrue(login_btn["enabled"])
        self.assertEqual(login_btn["bounds"], [200, 900, 880, 1050])
        self.assertEqual(login_btn["center"], [540, 975])

        # Check scrollable element
        scroll_elem = next((e for e in elements if e["element_id"] == "com.example.zeroapp:id/scroll_container"), None)
        self.assertIsNotNone(scroll_elem)
        self.assertTrue(scroll_elem["scrollable"])

    def test_fallback_element_id(self) -> None:
        elements = parse_ui_hierarchy(self.sample_xml, filter_useful=True)
        forgot_pw = next((e for e in elements if e["text"] == "Forgot Password?"), None)
        self.assertIsNotNone(forgot_pw)
        # Resource ID was empty, should have generated a fallback ID
        self.assertTrue(forgot_pw["element_id"].startswith("elem_"))
        self.assertIn("textview", forgot_pw["element_id"])

    def test_parse_ui_hierarchy_without_filter(self) -> None:
        all_elements = parse_ui_hierarchy(self.sample_xml, filter_useful=False)
        # FrameLayout and LinearLayout included
        self.assertEqual(len(all_elements), 9)

    def test_parse_empty_or_malformed_xml(self) -> None:
        self.assertEqual(parse_ui_hierarchy(""), [])
        with self.assertRaises(ValueError):
            parse_ui_hierarchy("<invalid xml")

    def test_duplicate_resource_ids_no_collision(self) -> None:
        xml = """<hierarchy rotation="0">
          <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.shop" bounds="[0,0][1080,2400]">
            <node index="0" text="Item Alpha" resource-id="com.example.shop:id/item_row" class="android.widget.TextView" package="com.example.shop" clickable="true" enabled="true" bounds="[0,100][1080,200]" />
            <node index="1" text="Item Beta" resource-id="com.example.shop:id/item_row" class="android.widget.TextView" package="com.example.shop" clickable="true" enabled="true" bounds="[0,200][1080,300]" />
            <node index="2" text="Item Gamma" resource-id="com.example.shop:id/item_row" class="android.widget.TextView" package="com.example.shop" clickable="true" enabled="true" bounds="[0,300][1080,400]" />
          </node>
        </hierarchy>"""
        elements = parse_ui_hierarchy(xml, filter_useful=True)
        self.assertEqual(len(elements), 3)

        # Ensure all element_ids are distinct (no collision!)
        element_ids = [e["element_id"] for e in elements]
        self.assertEqual(len(set(element_ids)), 3)
        self.assertEqual(element_ids, [
            "com.example.shop:id/item_row_0",
            "com.example.shop:id/item_row_1",
            "com.example.shop:id/item_row_2",
        ])

        # Raw resource_id is preserved on all
        for elem in elements:
            self.assertEqual(elem["resource_id"], "com.example.shop:id/item_row")

        # Bounds and centers are distinct
        self.assertEqual(elements[0]["bounds"], [0, 100, 1080, 200])
        self.assertEqual(elements[1]["bounds"], [0, 200, 1080, 300])
        self.assertEqual(elements[2]["bounds"], [0, 300, 1080, 400])
        self.assertEqual(elements[0]["center"], [540, 150])
        self.assertEqual(elements[1]["center"], [540, 250])
        self.assertEqual(elements[2]["center"], [540, 350])

    def test_content_description_only_element(self) -> None:
        xml = """<hierarchy rotation="0">
          <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.shop" bounds="[0,0][1080,2400]">
            <node index="0" text="" content-desc="Shopping Cart Icon" resource-id="com.example.shop:id/btn_cart" class="android.widget.ImageView" package="com.example.shop" clickable="true" enabled="true" bounds="[900,100][1000,200]" />
          </node>
        </hierarchy>"""
        elements = parse_ui_hierarchy(xml, filter_useful=True)
        self.assertEqual(len(elements), 1)
        cart = elements[0]
        self.assertEqual(cart["content_description"], "Shopping Cart Icon")
        self.assertEqual(cart["text"], "")
        self.assertTrue(cart["clickable"])
        self.assertEqual(cart["element_id"], "com.example.shop:id/btn_cart")

    def test_clickable_and_disabled_elements(self) -> None:
        xml = """<hierarchy rotation="0">
          <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.shop" bounds="[0,0][1080,2400]">
            <node index="0" text="Submit Order" resource-id="com.example.shop:id/btn_submit" class="android.widget.Button" package="com.example.shop" clickable="true" enabled="false" bounds="[100,500][980,650]" />
          </node>
        </hierarchy>"""
        elements = parse_ui_hierarchy(xml, filter_useful=True)
        self.assertEqual(len(elements), 1)
        btn = elements[0]
        self.assertTrue(btn["clickable"])
        self.assertFalse(btn["enabled"])

    def test_scrollable_container(self) -> None:
        xml = """<hierarchy rotation="0">
          <node index="0" text="" resource-id="com.example.shop:id/recycler_view" class="androidx.recyclerview.widget.RecyclerView" package="com.example.shop" scrollable="true" clickable="false" enabled="true" bounds="[0,200][1080,2000]" />
        </hierarchy>"""
        elements = parse_ui_hierarchy(xml, filter_useful=True)
        self.assertEqual(len(elements), 1)
        self.assertTrue(elements[0]["scrollable"])
        self.assertEqual(elements[0]["bounds"], [0, 200, 1080, 2000])

    def test_input_type_and_password(self) -> None:
        xml = """<hierarchy rotation="0">
          <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.example.shop" bounds="[0,0][1080,2400]">
            <node index="0" text="" resource-id="com.example.shop:id/pw" class="android.widget.EditText" package="com.example.shop" password="true" bounds="[100,200][980,350]" />
            <node index="1" text="" resource-id="com.example.shop:id/email" class="android.widget.EditText" package="com.example.shop" password="false" bounds="[100,400][980,550]" />
          </node>
        </hierarchy>"""
        elements = parse_ui_hierarchy(xml, filter_useful=True)
        self.assertEqual(len(elements), 2)
        pw_elem = elements[0]
        self.assertTrue(pw_elem["password"])
        self.assertEqual(pw_elem["input_type"], "password")

        email_elem = elements[1]
        self.assertFalse(email_elem["password"])
        self.assertEqual(email_elem["input_type"], "text")

    def test_deterministic_ids_across_repeated_parses(self) -> None:
        run1 = parse_ui_hierarchy(self.sample_xml)
        run2 = parse_ui_hierarchy(self.sample_xml)
        self.assertEqual(len(run1), len(run2))
        for e1, e2 in zip(run1, run2):
            self.assertEqual(e1["element_id"], e2["element_id"])
            self.assertEqual(e1["bounds"], e2["bounds"])
            self.assertEqual(e1["center"], e2["center"])

    def test_system_ui_filtering(self) -> None:
        xml = """<hierarchy rotation="0">
          <node index="0" text="" class="android.widget.FrameLayout" bounds="[0,0][1080,2400]">
            <node index="0" text="9:41" resource-id="com.android.systemui:id/clock" class="android.widget.TextView" package="com.android.systemui" bounds="[50,10][150,50]" />
            <node index="1" text="Home Button" resource-id="com.android.systemui:id/home" class="android.widget.ImageView" package="com.android.systemui" clickable="true" bounds="[480,2300][600,2380]" />
            <node index="2" text="App Button" resource-id="com.example.app:id/btn" class="android.widget.Button" package="com.example.app" clickable="true" bounds="[100,500][980,650]" />
          </node>
        </hierarchy>"""
        # Filtered (default): systemui elements removed
        filtered = parse_ui_hierarchy(xml, filter_useful=True, filter_system_ui=True)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["element_id"], "com.example.app:id/btn")

        # Unfiltered: systemui elements included
        unfiltered = parse_ui_hierarchy(xml, filter_useful=True, filter_system_ui=False)
        self.assertEqual(len(unfiltered), 3)

    def test_ui_parser_class_query_methods(self) -> None:
        elements = UIParser.parse(self.sample_xml)
        # Find by ID
        btn = UIParser.find_element_by_id(elements, "com.example.zeroapp:id/login_button")
        self.assertIsNotNone(btn)
        self.assertEqual(btn["text"], "Sign In")

        # Find by text (exact and partial)
        exact = UIParser.find_elements_by_text(elements, "Sign In", exact=True)
        self.assertEqual(len(exact), 1)
        self.assertEqual(exact[0]["element_id"], "com.example.zeroapp:id/login_button")

        partial = UIParser.find_elements_by_text(elements, "sign", exact=False)
        self.assertGreaterEqual(len(partial), 1)


if __name__ == "__main__":
    unittest.main()
