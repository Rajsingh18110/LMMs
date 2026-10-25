"""
benchmarks/readxhub_integration.py

Real-world integration test and benchmark workflow for https://readxhub.in.
Executes genuine browser control through LMMs BrowserTool:
  1. Opens https://readxhub.in homepage.
  2. Inspects rendered DOM and available navigation controls.
  3. Discovers real sign-in/login route rather than guessing.
  4. Navigates to discovered route (Auth0 Universal Login).
  5. Inspects login form elements (#username, #password, continue button).
  6. Securely checks for authorized test credentials (READXHUB_TEST_EMAIL, READXHUB_TEST_PASSWORD).
  7. If credentials exist, fills and submits form, then verifies authentication.
  8. If credentials do not exist, pauses and reports blocker without guessing.
"""

from __future__ import annotations

import os
import json
import time
from typing import Dict, Any
from lmms.backend.tools.browser import get_browser_tool


def run_readxhub_login_workflow(headless: bool = True) -> Dict[str, Any]:
    """
    Executes the stage-by-stage real-world ReadXHub workflow.
    Returns structured results for each independent stage.
    """
    stages = {
        "stage_1_homepage_opened": {
            "status": "PENDING",
            "evidence": "",
            "url": "",
            "title": ""
        },
        "stage_2_dom_inspected": {
            "status": "PENDING",
            "evidence": "",
            "login_control_found": False,
            "selector": ""
        },
        "stage_3_route_discovered": {
            "status": "PENDING",
            "evidence": "",
            "target_url": ""
        },
        "stage_4_login_form_inspected": {
            "status": "PENDING",
            "evidence": "",
            "username_field": "",
            "password_field": "",
            "submit_button": ""
        },
        "stage_5_credentials_supplied": {
            "status": "PENDING",
            "evidence": ""
        },
        "stage_6_form_submitted": {
            "status": "PENDING",
            "evidence": ""
        },
        "stage_7_authentication_verified": {
            "status": "PENDING",
            "evidence": ""
        }
    }

    bt = get_browser_tool()
    try:
        # ── Stage 1: Open real homepage ──────────────────────────────────────
        home_url = "https://readxhub.in/"
        res_open = bt.open_url(home_url, headless=headless)
        page_url = bt.page.url if bt.page else ""
        page_title = bt.page.title() if bt.page else ""

        if bt.page and "readxhub.in" in page_url:
            stages["stage_1_homepage_opened"]["status"] = "PASSED"
            stages["stage_1_homepage_opened"]["url"] = page_url
            stages["stage_1_homepage_opened"]["title"] = page_title
            stages["stage_1_homepage_opened"]["evidence"] = f"Successfully opened {page_url} (Title: '{page_title}')"
        else:
            stages["stage_1_homepage_opened"]["status"] = "FAILED"
            stages["stage_1_homepage_opened"]["evidence"] = f"Failed to reach {home_url}. Got: {page_url}"
            return {"overall_status": "FAILED", "stages": stages}

        # ── Stage 2: Inspect rendered DOM for login controls ──────────────────
        dom_preview = bt.get_interactive_dom()
        login_btn_selector = ""
        for line in dom_preview.splitlines():
            line_str = line.strip()
            if "Login / Signup" in line_str or ("Login" in line_str and "<button" in line_str):
                # Extract selector
                if "selector='" in line_str:
                    sel_part = line_str.split("selector='")[1].split("'")[0]
                    login_btn_selector = sel_part
                    break

        if login_btn_selector:
            stages["stage_2_dom_inspected"]["status"] = "PASSED"
            stages["stage_2_dom_inspected"]["login_control_found"] = True
            stages["stage_2_dom_inspected"]["selector"] = login_btn_selector
            stages["stage_2_dom_inspected"]["evidence"] = f"Discovered login button from DOM: '{login_btn_selector}'"
        else:
            stages["stage_2_dom_inspected"]["status"] = "FAILED"
            stages["stage_2_dom_inspected"]["evidence"] = "Login control not found in rendered DOM"
            return {"overall_status": "FAILED", "stages": stages}

        # ── Stage 3: Click discovered control and observe navigation ──────────
        click_res = bt.click_element(login_btn_selector)
        time.sleep(1.0)
        new_url = bt.page.url if bt.page else ""
        new_title = bt.page.title() if bt.page else ""

        if "auth0.com" in new_url or "/u/login" in new_url or "login" in new_url.lower():
            stages["stage_3_route_discovered"]["status"] = "PASSED"
            stages["stage_3_route_discovered"]["target_url"] = new_url
            stages["stage_3_route_discovered"]["evidence"] = f"Navigated to real authentication route: {new_url} (Title: '{new_title}')"
        else:
            stages["stage_3_route_discovered"]["status"] = "FAILED"
            stages["stage_3_route_discovered"]["evidence"] = f"Click did not navigate to expected login route. URL: {new_url}"
            return {"overall_status": "FAILED", "stages": stages}

        # ── Stage 4: Inspect real login form elements ─────────────────────────
        auth_dom = bt.get_interactive_dom()
        username_sel = ""
        password_sel = ""
        submit_sel = ""

        if bt.page:
            if bt.page.locator("#username").count() > 0:
                username_sel = "#username"
            if bt.page.locator("#password").count() > 0:
                password_sel = "#password"
            if bt.page.locator('button[name="action"]').count() > 0:
                submit_sel = 'button[name="action"]'
            elif bt.page.locator('button[type="submit"]').count() > 0:
                submit_sel = 'button[type="submit"]'

        if username_sel and password_sel and submit_sel:
            stages["stage_4_login_form_inspected"]["status"] = "PASSED"
            stages["stage_4_login_form_inspected"]["username_field"] = username_sel
            stages["stage_4_login_form_inspected"]["password_field"] = password_sel
            stages["stage_4_login_form_inspected"]["submit_button"] = submit_sel
            stages["stage_4_login_form_inspected"]["evidence"] = (
                f"Inspected real login form: username='{username_sel}', "
                f"password='{password_sel}', submit='{submit_sel}'"
            )
        else:
            stages["stage_4_login_form_inspected"]["status"] = "FAILED"
            stages["stage_4_login_form_inspected"]["evidence"] = f"Missing login fields on {new_url}"
            return {"overall_status": "FAILED", "stages": stages}

        # ── Stage 5: Credential authorization check ───────────────────────────
        test_email = os.getenv("READXHUB_TEST_EMAIL", "").strip()
        test_password = os.getenv("READXHUB_TEST_PASSWORD", "").strip()

        if not test_email or not test_password:
            # Secure pause & report requirement: NEVER invent or guess passwords
            stages["stage_5_credentials_supplied"]["status"] = "AWAITING_USER_CREDENTIALS"
            stages["stage_5_credentials_supplied"]["evidence"] = (
                "PAUSED per security policy: No authorized credentials configured in environment "
                "(READXHUB_TEST_EMAIL / READXHUB_TEST_PASSWORD). Credentials must never be invented."
            )
            stages["stage_6_form_submitted"]["status"] = "SKIPPED_PENDING_CREDENTIALS"
            stages["stage_6_form_submitted"]["evidence"] = "Form submission skipped because no authorized credentials were provided."
            stages["stage_7_authentication_verified"]["status"] = "UNVERIFIED"
            stages["stage_7_authentication_verified"]["evidence"] = "Authentication unverified: awaiting authorized test credentials."
            return {
                "overall_status": "PASSED_UP_TO_CREDENTIAL_PROMPT",
                "stages": stages
            }

        # If credentials provided: execute secure login
        stages["stage_5_credentials_supplied"]["status"] = "PASSED"
        stages["stage_5_credentials_supplied"]["evidence"] = "Authorized credentials supplied via secure environment."

        # ── Stage 6: Fill form and submit ─────────────────────────────────────
        fill_res = bt.fill_form({
            username_sel: test_email,
            password_sel: test_password
        })
        time.sleep(0.5)
        submit_res = bt.click_element(submit_sel)
        time.sleep(2.0)
        stages["stage_6_form_submitted"]["status"] = "PASSED"
        stages["stage_6_form_submitted"]["evidence"] = f"Submitted credentials: {submit_res}"

        # ── Stage 7: Verify authenticated session ─────────────────────────────
        post_url = bt.page.url if bt.page else ""
        acct_ctx = bt.get_account_context(force_refresh=True)

        verified = (
            "readxhub.in" in post_url
            and "auth0.com" not in post_url
            and acct_ctx.get("status") == "verified"
        )

        if verified:
            stages["stage_7_authentication_verified"]["status"] = "PASSED"
            stages["stage_7_authentication_verified"]["evidence"] = f"Successfully verified authenticated session on {post_url}"
            return {"overall_status": "PASSED", "stages": stages}
        else:
            stages["stage_7_authentication_verified"]["status"] = "UNVERIFIED"
            stages["stage_7_authentication_verified"]["evidence"] = f"Authentication not verified on {post_url}. Auth context: {acct_ctx.get('status')}"
            return {"overall_status": "PARTIAL_SUCCESS", "stages": stages}

    finally:
        bt.close()


if __name__ == "__main__":
    result = run_readxhub_login_workflow(headless=True)
    print(json.dumps(result, indent=2))
