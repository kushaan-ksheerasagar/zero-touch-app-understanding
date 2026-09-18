"""
Comprehensive manual smoke test for ZeroTouch Demo Android app.

Navigates and verifies all 6 screens:
1. LoginActivity (input email/password, tap login)
2. HomeActivity (scroll, tap search, product cards, profile)
3. SearchActivity (input query, category chips, tap search)
4. ResultsActivity (scroll, tap result card)
5. ProductActivity (view details, back navigation)
6. ProfileActivity (view settings, back navigation)
"""

import os
import sys
import time

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_CONTROLLER_DIR = os.path.join(PROJECT_ROOT, "android-controller")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if ANDROID_CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, ANDROID_CONTROLLER_DIR)

# Ensure platform-tools on PATH
sdk_tools = os.path.expanduser(r"~\AppData\Local\Android\Sdk\platform-tools")
if os.path.exists(sdk_tools) and sdk_tools not in os.environ.get("PATH", ""):
    os.environ["PATH"] = sdk_tools + os.pathsep + os.environ.get("PATH", "")

from controller import AndroidController


def find_elem(state, el_id=None, text=None):
    elements = state.get("elements", [])
    for el in elements:
        eid = el.get("element_id") if isinstance(el, dict) else getattr(el, "element_id", None)
        t_val = el.get("text") if isinstance(el, dict) else getattr(el, "text", None)
        if el_id and eid == el_id:
            return el
        if text and t_val and text.lower() in t_val.lower():
            return el
    return None


def get_attr(el, attr, default=None):
    if el is None:
        return default
    if isinstance(el, dict):
        return el.get(attr, default)
    return getattr(el, attr, default)


def run_smoke_test():
    print("=== STARTING ZEROTOUCH DEMO APP SMOKE TEST ===")
    ctrl = AndroidController()
    device_id = ctrl.connect(device_id="emulator-5554")
    print(f"Connected to Android device: {device_id}")

    # Step 1: Launch LoginActivity
    print("\n--- 1. Testing Login Screen ---")
    ctrl.adb_client.run_command(["shell", "am", "force-stop", "com.zerotouch.demo"], check=False)
    time.sleep(0.5)
    ctrl.launch_app("com.zerotouch.demo", ".LoginActivity")
    time.sleep(1.5)
    s1 = ctrl.get_current_state()
    act1 = s1.get("current_activity", "")
    print(f"Current Activity: {act1}")
    assert "LoginActivity" in act1, f"Expected LoginActivity, got {act1}"

    title_elem = find_elem(s1, el_id="com.zerotouch.demo:id/text_login_title")
    email_elem = find_elem(s1, el_id="com.zerotouch.demo:id/input_email")
    pwd_elem = find_elem(s1, el_id="com.zerotouch.demo:id/input_password")
    login_btn = find_elem(s1, el_id="com.zerotouch.demo:id/btn_login")

    print(f"  Title element: {get_attr(title_elem, 'text')}")
    print(f"  Email input element: {get_attr(email_elem, 'element_id')}")
    print(f"  Password input element: {get_attr(pwd_elem, 'element_id')}")
    print(f"  Login button: {get_attr(login_btn, 'text')}")

    assert title_elem and get_attr(title_elem, "text") == "ZeroTouch"
    assert email_elem and "EditText" in get_attr(email_elem, "type", "")
    assert pwd_elem and "EditText" in get_attr(pwd_elem, "type", "")
    assert login_btn and get_attr(login_btn, "clickable")

    # Type credentials and login
    print("  Typing test credentials into input_email and input_password...")
    ctrl.execute_action({"action": "type", "target": {"element_id": "com.zerotouch.demo:id/input_email"}, "text": "demo.tester@zerotouch.app"})
    time.sleep(0.5)
    ctrl.execute_action({"action": "type", "target": {"element_id": "com.zerotouch.demo:id/input_password"}, "text": "secret123"})
    time.sleep(0.5)
    # Dismiss soft keyboard if visible so it doesn't obstruct tap targets
    ctrl.adb_client.press_back()
    time.sleep(0.5)
    ctrl.get_current_state()

    print("  Tapping Login button...")
    ctrl.execute_action({"action": "tap", "target": {"element_id": "com.zerotouch.demo:id/btn_login"}})
    time.sleep(1.5)

    # Step 2: HomeActivity
    print("\n--- 2. Testing Home Screen ---")
    s2 = ctrl.get_current_state()
    act2 = s2.get("current_activity", "")
    print(f"Current Activity: {act2}")
    assert "HomeActivity" in act2, f"Expected HomeActivity, got {act2}"

    welcome_elem = find_elem(s2, el_id="com.zerotouch.demo:id/text_home_welcome")
    search_btn = find_elem(s2, el_id="com.zerotouch.demo:id/btn_search")
    profile_btn = find_elem(s2, el_id="com.zerotouch.demo:id/btn_profile")
    card1 = find_elem(s2, el_id="com.zerotouch.demo:id/card_product_1")
    scroll_elem = find_elem(s2, el_id="com.zerotouch.demo:id/home_scroll")

    print(f"  Welcome element: {get_attr(welcome_elem, 'text')}")
    print(f"  Search button: {get_attr(search_btn, 'element_id')}")
    print(f"  Profile button: {get_attr(profile_btn, 'text')}")
    print(f"  Product card 1: {get_attr(card1, 'element_id')}")
    print(f"  Scroll container: {get_attr(scroll_elem, 'element_id')} (scrollable={get_attr(scroll_elem, 'scrollable')})")

    assert welcome_elem and "Welcome" in get_attr(welcome_elem, "text")
    assert search_btn and get_attr(search_btn, "clickable")
    assert profile_btn and get_attr(profile_btn, "clickable")
    assert scroll_elem and get_attr(scroll_elem, "scrollable")

    print("  Testing scroll on Home screen...")
    ctrl.execute_action({"action": "scroll", "direction": "down"})
    time.sleep(0.8)
    ctrl.execute_action({"action": "scroll", "direction": "up"})
    time.sleep(0.8)

    # Tap search button to navigate to SearchActivity
    print("  Tapping Search button -> SearchActivity...")
    ctrl.execute_action({"action": "tap", "target": {"element_id": "com.zerotouch.demo:id/btn_search"}})
    time.sleep(1.5)

    # Step 3: SearchActivity
    print("\n--- 3. Testing Search Screen ---")
    s3 = ctrl.get_current_state()
    act3 = s3.get("current_activity", "")
    print(f"Current Activity: {act3}")
    assert "SearchActivity" in act3, f"Expected SearchActivity, got {act3}"

    search_input = find_elem(s3, el_id="com.zerotouch.demo:id/input_search")
    do_search_btn = find_elem(s3, el_id="com.zerotouch.demo:id/btn_do_search")
    chip_elem = find_elem(s3, el_id="com.zerotouch.demo:id/chip_headphones")
    back_btn_3 = find_elem(s3, el_id="com.zerotouch.demo:id/btn_back")

    print(f"  Search input: {get_attr(search_input, 'element_id')}")
    print(f"  Search button: {get_attr(do_search_btn, 'text')}")
    print(f"  Category chip: {get_attr(chip_elem, 'text')}")
    print(f"  Back button: {get_attr(back_btn_3, 'text')}")

    assert search_input and "EditText" in get_attr(search_input, "type", "")
    assert do_search_btn and get_attr(do_search_btn, "clickable")
    assert chip_elem and get_attr(chip_elem, "clickable")

    print("  Typing search query 'Noise Cancelling'...")
    ctrl.execute_action({"action": "type", "target": {"element_id": "com.zerotouch.demo:id/input_search"}, "text": "Noise Cancelling"})
    time.sleep(0.5)
    # Dismiss soft keyboard
    ctrl.adb_client.press_back()
    time.sleep(0.5)
    ctrl.get_current_state()

    print("  Tapping Search action button -> ResultsActivity...")
    ctrl.execute_action({"action": "tap", "target": {"element_id": "com.zerotouch.demo:id/btn_do_search"}})
    time.sleep(1.5)

    # Step 4: ResultsActivity
    print("\n--- 4. Testing Results Screen ---")
    s4 = ctrl.get_current_state()
    act4 = s4.get("current_activity", "")
    print(f"Current Activity: {act4}")
    assert "ResultsActivity" in act4, f"Expected ResultsActivity, got {act4}"

    results_title = find_elem(s4, el_id="com.zerotouch.demo:id/text_results_title")
    res_card1 = find_elem(s4, el_id="com.zerotouch.demo:id/result_card_1")
    res_card2 = find_elem(s4, el_id="com.zerotouch.demo:id/result_card_2")
    res_scroll = find_elem(s4, el_id="com.zerotouch.demo:id/results_scroll")

    print(f"  Results title: {get_attr(results_title, 'text')}")
    print(f"  Result card 1: {get_attr(res_card1, 'element_id')}")
    print(f"  Result card 2: {get_attr(res_card2, 'element_id')}")
    print(f"  Results scroll container: {get_attr(res_scroll, 'element_id')} (scrollable={get_attr(res_scroll, 'scrollable')})")

    assert results_title and "Noise Cancelling" in get_attr(results_title, "text")
    assert res_card1 and get_attr(res_card1, "clickable")
    assert res_scroll and get_attr(res_scroll, "scrollable")

    print("  Testing scroll on Results screen...")
    ctrl.execute_action({"action": "scroll", "direction": "down"})
    time.sleep(0.8)

    print("  Tapping Result Card 1 -> ProductActivity...")
    ctrl.execute_action({"action": "tap", "target": {"element_id": "com.zerotouch.demo:id/result_card_1"}})
    time.sleep(1.5)

    # Step 5: ProductActivity
    print("\n--- 5. Testing Product Screen ---")
    s5 = ctrl.get_current_state()
    act5 = s5.get("current_activity", "")
    print(f"Current Activity: {act5}")
    assert "ProductActivity" in act5, f"Expected ProductActivity, got {act5}"

    prod_name = find_elem(s5, el_id="com.zerotouch.demo:id/text_product_name")
    prod_price = find_elem(s5, el_id="com.zerotouch.demo:id/text_product_price")
    prod_desc = find_elem(s5, el_id="com.zerotouch.demo:id/text_product_description")
    prod_img = find_elem(s5, el_id="com.zerotouch.demo:id/image_product")

    print(f"  Product Name: {get_attr(prod_name, 'text')}")
    print(f"  Product Price: {get_attr(prod_price, 'text')}")
    print(f"  Product Description: {get_attr(prod_desc, 'text')[:50]}...")
    print(f"  Product Image Preview: {get_attr(prod_img, 'element_id')}")

    assert prod_name and len(get_attr(prod_name, "text")) > 0
    assert prod_price and "$" in get_attr(prod_price, "text")
    assert prod_desc and len(get_attr(prod_desc, "text")) > 0

    print("  Testing Back Navigation (Product -> Results -> Search -> Home)...")
    ctrl.execute_action({"action": "back"})
    time.sleep(1.0)
    assert "ResultsActivity" in ctrl.get_current_state().get("current_activity", "")
    print("  Returned to ResultsActivity")

    ctrl.execute_action({"action": "back"})
    time.sleep(1.0)
    assert "SearchActivity" in ctrl.get_current_state().get("current_activity", "")
    print("  Returned to SearchActivity")

    ctrl.execute_action({"action": "back"})
    time.sleep(1.0)
    assert "HomeActivity" in ctrl.get_current_state().get("current_activity", "")
    print("  Returned to HomeActivity")

    # Step 6: ProfileActivity
    print("\n--- 6. Testing Profile Screen ---")
    print("  Tapping Profile button -> ProfileActivity...")
    ctrl.execute_action({"action": "tap", "target": {"element_id": "com.zerotouch.demo:id/btn_profile"}})
    time.sleep(1.5)

    s6 = ctrl.get_current_state()
    act6 = s6.get("current_activity", "")
    print(f"Current Activity: {act6}")
    assert "ProfileActivity" in act6, f"Expected ProfileActivity, got {act6}"

    user_name = find_elem(s6, el_id="com.zerotouch.demo:id/text_user_name")
    user_email = find_elem(s6, el_id="com.zerotouch.demo:id/text_user_email")
    row_account = find_elem(s6, el_id="com.zerotouch.demo:id/row_account")
    row_notif = find_elem(s6, el_id="com.zerotouch.demo:id/row_notifications")

    print(f"  User Name: {get_attr(user_name, 'text')}")
    print(f"  User Email: {get_attr(user_email, 'text')}")
    print(f"  Settings Row Account: {get_attr(row_account, 'element_id')} (clickable={get_attr(row_account, 'clickable')})")
    print(f"  Settings Row Notifications: {get_attr(row_notif, 'element_id')} (clickable={get_attr(row_notif, 'clickable')})")

    assert user_name and get_attr(user_name, "text") == "Alex Mercer"
    assert user_email and get_attr(user_email, "text") == "alex.mercer@example.com"
    assert row_account and get_attr(row_account, "clickable")

    print("  Tapping Back from Profile -> Home...")
    ctrl.execute_action({"action": "back"})
    time.sleep(1.0)
    s_final = ctrl.get_current_state()
    act_final = s_final.get("current_activity", "")
    print(f"Final Activity: {act_final}")
    assert "HomeActivity" in act_final

    print("\n==================================================")
    print("ALL 6 SCREENS AND ALL TRANSITIONS TESTED AND VERIFIED SUCCESSFULLY!")
    print("==================================================")
    return True


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
