"""
Unit tests for UIParser.
"""

import os
import sys
import unittest

# Ensure android-controller directory is in sys.path
CONTROLLER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, CONTROLLER_DIR)

from ui_parser import UIParser, compute_center, parse_bounds



class TestUIParser(unittest.TestCase):
    """Test suite for UIAutomator XML parsing and element extraction."""

    def setUp(self) -> None:
        self.sample_xml_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "sample_dump.xml"
        )
        with open(self.sample_xml_path, "r", encoding="utf-8") as f:
            self.sample_xml = f.read()

    def test_parse_bounds_valid(self) -> None:
        bounds = parse_bounds("[0,70][1080,210]")
        self.assertEqual(bounds, (0, 70, 1080, 210))

    def test_parse_bounds_invalid(self) -> None:
        self.assertIsNone(parse_bounds(""))
        self.assertIsNone(parse_bounds("invalid_bounds"))
        self.assertIsNone(parse_bounds("[0,0]"))

    def test_compute_center(self) -> None:
        center = compute_center((100, 200, 300, 400))
        self.assertEqual(center, (200, 300))

    def test_parse_sample_dump(self) -> None:
        elements = UIParser.parse(self.sample_xml, filter_containers=True)
        self.assertGreater(len(elements), 0)

        # Verify element structure
        for elem in elements:
            self.assertIn("element_id", elem)
            self.assertIn("type", elem)
            self.assertIn("text", elem)
            self.assertIn("content_description", elem)
            self.assertIn("bounds", elem)
            self.assertIn("center", elem)
            self.assertIn("clickable", elem)
            self.assertIn("scrollable", elem)
            self.assertIn("focusable", elem)
            self.assertIn("enabled", elem)
            self.assertEqual(len(elem["bounds"]), 4)
            self.assertEqual(len(elem["center"]), 2)

    def test_element_with_resource_id(self) -> None:
        elements = UIParser.parse(self.sample_xml, filter_containers=True)
        btn_search = UIParser.find_element_by_id(elements, "com.example.shop:id/btn_search")
        self.assertIsNotNone(btn_search)
        self.assertEqual(btn_search["content_description"], "Search Store")
        self.assertTrue(btn_search["clickable"])
        self.assertEqual(btn_search["bounds"], [940, 90, 1040, 190])
        self.assertEqual(btn_search["center"], [990, 140])

    def test_deterministic_fallback_id(self) -> None:
        elements = UIParser.parse(self.sample_xml, filter_containers=True)
        # In sample_dump.xml, Product Item 1 has an Add to Cart ImageButton without resource-id
        cart_buttons = [e for e in elements if e["content_description"] == "Add to Cart"]
        self.assertGreater(len(cart_buttons), 0)

        first_cart = cart_buttons[0]
        self.assertTrue(first_cart["element_id"].startswith("elem_"))
        self.assertIn("ImageButton", first_cart["element_id"])
        self.assertIn("900_910", first_cart["element_id"])

    def test_filter_containers(self) -> None:
        raw_elements = UIParser.parse(self.sample_xml, filter_containers=False)
        filtered_elements = UIParser.parse(self.sample_xml, filter_containers=True)

        # Filtered elements should be fewer than raw elements because layout wrappers are filtered
        self.assertLess(len(filtered_elements), len(raw_elements))

        # But all interactive or informative elements should still exist
        signin_btn = UIParser.find_element_by_id(filtered_elements, "com.example.shop:id/btn_signin")
        self.assertIsNotNone(signin_btn)
        self.assertEqual(signin_btn["text"], "Sign In")
        self.assertTrue(signin_btn["clickable"])

    def test_find_element_by_id_missing(self) -> None:
        elements = UIParser.parse(self.sample_xml)
        elem = UIParser.find_element_by_id(elements, "non.existent:id/button")
        self.assertIsNone(elem)

    def test_find_elements_by_text(self) -> None:
        elements = UIParser.parse(self.sample_xml)
        exact = UIParser.find_elements_by_text(elements, "Sign In", exact=True)
        self.assertEqual(len(exact), 1)
        self.assertEqual(exact[0]["element_id"], "com.example.shop:id/btn_signin")

        partial = UIParser.find_elements_by_text(elements, "sign", exact=False)
        self.assertGreaterEqual(len(partial), 1)

    def test_empty_or_malformed_xml(self) -> None:
        self.assertEqual(UIParser.parse(""), [])
        self.assertEqual(UIParser.parse("   \n  "), [])
        with self.assertRaises(ValueError):
            UIParser.parse("<incomplete_xml><node")


if __name__ == "__main__":
    unittest.main()
