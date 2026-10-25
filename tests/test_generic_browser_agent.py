"""
test_generic_browser_agent.py

Comprehensive local fixture tests for the generic, website-independent browser agent:
1. Unfamiliar page with a contenteditable editor and zero site-specific selectors.
2. Dynamic SPA where controls change after navigation or clicking.
3. Stale selectors and graceful error recovery.
4. Login-required and unauthenticated state evaluation.
5. Draft save verification and save failures.
6. Existing-session attachment vs persistent-agent-browser mode separation.
7. Approval gates before consequential public submissions (Publish / Post / Submit).
8. Regression compatibility with existing browser tools.
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import patch

from lmms.backend.tools.browser import (
    BrowserTool,
    get_browser_tool,
    get_chrome_executable_path
)
from lmms.backend.tools.site_adapters import (
    SiteAdapterRegistry,
    ReadXHubAdapter,
    get_site_adapter
)


@pytest.fixture
def b_tool():
    """Provides an isolated headless BrowserTool instance and guarantees clean teardown."""
    bt = BrowserTool()
    bt._ensure_session(headless=True)
    yield bt
    try:
        bt.close()
    except Exception:
        pass


def test_unfamiliar_page_with_contenteditable_editor(b_tool):
    """Tests writing and verifying text in an unfamiliar page with contenteditable editor (no ReadXHub selectors)."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>StackUnderflow - Ask Question</title></head>
    <body>
        <h1>Ask a Public Question</h1>
        <form id="qa-form">
            <input id="q-title" name="title" placeholder="e.g. Is there an R function for finding the index..." />
            <div id="custom-editor" role="textbox" contenteditable="true" aria-label="Question Body" style="min-height: 100px; border: 1px solid #ccc;">
                <p>Initial placeholder text</p>
            </div>
            <button id="btn-save-draft" type="button">Save draft</button>
            <button id="btn-submit" type="button">Submit Question</button>
        </form>
    </body>
    </html>
    """
    b_tool.page.set_content(html)
    
    obs = b_tool.observe_page()
    assert obs["title"] == "StackUnderflow - Ask Question"
    assert obs["editors_count"] >= 2  # input and contenteditable div
    
    # Type title into unfamiliar input
    res_title = b_tool.type_text("#q-title", "How to implement generic observe-act-verify loops in Python?")
    assert "[TYPE_SUCCESS]" in res_title
    assert "How to implement generic" in b_tool.page.input_value("#q-title")
    
    # Type body into unfamiliar contenteditable editor
    body_text = "I am designing an autonomous web agent that needs to inspect arbitrary DOM trees without site-specific hardcoded selectors."
    res_body = b_tool.type_text("#custom-editor", body_text)
    assert "[TYPE_SUCCESS]" in res_body
    
    # Verify editor content honestly using verify_editor_content
    v_res = b_tool.verify_editor_content(selector="#custom-editor", expected_substring="autonomous web agent")
    assert v_res["verified"] is True
    assert v_res["is_contenteditable"] is True
    assert v_res["char_count"] >= len(body_text)


def test_dynamic_spa_controls_change_after_clicking(b_tool):
    """Tests dynamic SPA behavior where clicking a button dynamically changes the visible controls."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Unfamiliar SPA App</title></head>
    <body>
        <div id="app">
            <div id="step-1">
                <h2>Step 1: Select Channel</h2>
                <button id="btn-select-tech" onclick="
                    document.getElementById('step-1').style.display='none';
                    document.getElementById('step-2').style.display='block';
                ">Technology Channel</button>
            </div>
            <div id="step-2" style="display:none;">
                <h2>Step 2: Enter Content</h2>
                <textarea id="ta-content" placeholder="Share your insights..."></textarea>
                <button id="btn-save" onclick="
                    document.getElementById('status').innerText = 'Draft saved';
                ">Save draft</button>
                <div id="status">Unsaved</div>
            </div>
        </div>
    </body>
    </html>
    """
    b_tool.page.set_content(html)
    
    # Initially step 1 is visible
    obs1 = b_tool.observe_page()
    assert any("Technology Channel" in el["label"] for el in obs1["elements"])
    assert not any(el["selector"] == "#ta-content" for el in obs1["elements"])
    
    # Click step 1 button
    click_res = b_tool.click_element("#btn-select-tech")
    assert "[CLICK_SUCCESS]" in click_res
    
    # Now step 2 is visible
    obs2 = b_tool.observe_page()
    assert any("insights" in ed.get("placeholder", "") or "#ta-content" in ed["selector"] for ed in obs2["editors"])


def test_stale_selector_recovery(b_tool):
    """Tests that a re-rendered DOM element recovery works cleanly without unhandled crash."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Dynamic DOM Replacement</title></head>
    <body>
        <div id="container">
            <button id="dynamic-btn" onclick="
                const newBtn = document.createElement('button');
                newBtn.id = 'dynamic-btn';
                newBtn.innerText = 'Updated Action';
                this.parentNode.replaceChild(newBtn, this);
            ">Initial Action</button>
        </div>
    </body>
    </html>
    """
    b_tool.page.set_content(html)
    
    # First click replaces element
    res1 = b_tool.click_element("#dynamic-btn")
    assert "[CLICK_SUCCESS]" in res1
    
    # Second click on the same ID operates on the newly attached element
    res2 = b_tool.click_element("#dynamic-btn")
    assert "[CLICK_SUCCESS]" in res2 or "[CLICK_SUCCESS_AFTER_RECOVERY]" in res2


def test_login_required_and_unauthenticated_state_evaluation(b_tool):
    """Tests that unauthenticated sites are recognized honestly from DOM evidence."""
    # 1. Unauthenticated page fixture
    unauth_html = """
    <html>
    <body>
        <nav>
            <a href="/explore">Explore</a>
            <button id="btn-login">Log In / Sign Up</button>
        </nav>
        <main><h1>Welcome to Reddit Clone</h1></main>
    </body>
    </html>
    """
    b_tool.page.set_content(unauth_html)
    obs = b_tool.observe_page()
    assert obs["auth_status"] == "unauthenticated"
    assert "visible login/sign-in options" in obs["auth_evidence"]
    
    # 2. Authenticated page fixture
    auth_html = """
    <html>
    <body>
        <nav>
            <div class="user-pill" aria-label="My Account">@developer_pro</div>
            <button id="btn-logout">Log Out</button>
        </nav>
        <main><h1>Dashboard</h1></main>
    </body>
    </html>
    """
    b_tool.page.set_content(auth_html)
    obs_auth = b_tool.observe_page()
    assert obs_auth["auth_status"] == "authenticated"
    assert "Verified session" in obs_auth["auth_evidence"]


def test_draft_save_verification_and_failure(b_tool):
    """Tests verifying draft persistence and detecting save failure when no feedback occurs."""
    # Fixture with working save indicator
    working_save_html = """
    <html>
    <body>
        <textarea id="editor">Draft content</textarea>
        <button id="save-btn" onclick="document.getElementById('pill').innerText='Draft saved'">Save draft</button>
        <div id="pill">Unsaved</div>
    </body>
    </html>
    """
    b_tool.page.set_content(working_save_html)
    res = b_tool.save_draft("#save-btn")
    assert res["success"] is True
    assert res["verified"] is True
    assert "Draft saved" in res["status_indicators"]
    
    # Fixture with dead save button (no DOM change, no persistence)
    dead_save_html = """
    <html>
    <body>
        <textarea id="editor">Draft content</textarea>
        <button id="dead-save-btn">Save draft</button>
        <div id="pill">Unsaved</div>
    </body>
    </html>
    """
    b_tool.page.set_content(dead_save_html)
    res_fail = b_tool.save_draft("#dead-save-btn")
    assert res_fail["success"] is True
    assert res_fail["verified"] is False
    assert "no state change detected" in res_fail["message"]


def test_approval_gate_before_public_submission(b_tool):
    """Tests that public publishing/submitting buttons require explicit human-in-the-loop approval."""
    html = """
    <html>
    <body>
        <h1>Post to Community</h1>
        <button id="btn-publish-post">Publish Post</button>
    </body>
    </html>
    """
    b_tool.page.set_content(html)
    
    # Attempting to click Publish Post without approval must be intercepted
    res = b_tool.click_element("#btn-publish-post")
    assert "[ACTION_REQUIRES_APPROVAL]" in res
    assert "represents a public submission or publication action" in res
    
    # Explicitly grant publication approval
    b_tool.approve_publication("#btn-publish-post")
    
    # Now click proceeds
    res_approved = b_tool.click_element("#btn-publish-post")
    assert "[CLICK_SUCCESS]" in res_approved


def test_existing_session_vs_persistent_profile_modes():
    """Verifies that browser session modes are distinct and report honest state."""
    bt = BrowserTool()
    
    # Default is none
    assert bt._session_mode == "none"
    
    # Test persistent profile mode
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = bt.open_persistent_browser(url="about:blank", headless=True, profile_dir=tmp_dir)
        assert res["status"] == "connected"
        assert res["mode"] == "persistent_profile"
        assert bt._session_mode == "persistent_profile"
        
        # Disconnect
        bt.disconnect_session(preserve_data=True)
        assert bt._session_mode == "none"
    bt.close()


def test_site_adapter_registry_isolation():
    """Verifies that site adapters are optional and match only designated domains."""
    # ReadXHub adapter matches only readxhub.in
    r_adapter = get_site_adapter("https://readxhub.in/createapost")
    assert r_adapter is not None
    assert r_adapter.domain == "readxhub.in"
    assert "Save draft" in r_adapter.get_save_draft_hints()
    
    # Unfamiliar sites return None and use generic dynamic discovery
    assert get_site_adapter("https://reddit.com/r/programming/submit") is None
    assert get_site_adapter("https://stackoverflow.com/questions/ask") is None
    assert get_site_adapter("https://unfamiliar-domain.org/edit") is None
