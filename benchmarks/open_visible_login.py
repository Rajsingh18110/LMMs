"""
benchmarks/open_visible_login.py

Launches LMMs's persistent visible browser on DISPLAY=:0,
navigates to https://readxhub.in, clicks Login / Signup to display Auth0,
and keeps the window alive so the user can authenticate manually.
Monitors the page state and updates ~/.lmms/browser/preview.png.
"""

import sys
import os
import time

sys.path.insert(0, "/home/kali/Projects/LMMs")
from lmms.backend.tools.browser import get_browser_tool

def main():
    bt = get_browser_tool()
    print("[1/3] Opening persistent visible browser on DISPLAY=:0...")
    res = bt.open_persistent_browser("https://readxhub.in/", headless=False)
    print("Launch result:", res)
    time.sleep(2.0)

    print("[2/3] Inspecting DOM for Login / Signup control...")
    dom = bt.get_interactive_dom()
    login_sel = ""
    for line in dom.splitlines():
        if "Login / Signup" in line and "selector='" in line:
            login_sel = line.split("selector='")[1].split("'")[0]
            break

    if login_sel:
        print(f"[3/3] Clicking login control '{login_sel}' to open Auth0 login form...")
        bt.click_element(login_sel)
        time.sleep(2.0)
        print("Active Page URL:", bt.page.url if bt.page else "None")
        print("Active Page Title:", bt.page.title() if bt.page else "None")
        bt._capture_preview_snapshot(action="Awaiting user login on Auth0")
        print("Visible browser is now open on your screen awaiting manual authentication.")
    else:
        print("No login control found in DOM. Current URL:", bt.page.url if bt.page else "")

if __name__ == "__main__":
    main()
