"""
tests/test_persistent_session_and_cdp.py

Unit and integration tests for LMMs browser session authentication:
1. Profile locking detection (active process vs stale lock cleanup).
2. CDP endpoint verification and graceful failure handling.
3. Persistent browser session launching, retention, and reuse.
4. Session disconnection without data loss (preserving profile and cookies).
5. Context reuse across multiple browser operations.
6. Honest authentication state evaluation from live DOM evidence.
"""

import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

from lmms.backend.tools.browser import (
    BrowserTool,
    get_browser_tool,
    is_profile_locked,
    verify_cdp_endpoint,
    get_chrome_executable_path
)


@pytest.fixture(autouse=True)
def cleanup_browser():
    yield
    bt = get_browser_tool()
    try:
        bt.disconnect_session(preserve_data=True)
    except Exception:
        pass


def test_is_profile_locked_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initially unlocked
        locked, pid = is_profile_locked(tmp_dir)
        assert locked is False
        assert pid is None

        # Create lock symlink pointing to our own current process (which is alive)
        current_pid = os.getpid()
        lock_path = os.path.join(tmp_dir, "SingletonLock")
        os.symlink(f"test-host-{current_pid}", lock_path)

        locked, pid = is_profile_locked(tmp_dir)
        assert locked is True
        assert pid == current_pid

        # Create lock symlink pointing to an impossible/dead PID
        os.unlink(lock_path)
        dead_pid = 999999
        os.symlink(f"test-host-{dead_pid}", lock_path)

        # Stale lock should be detected and automatically unlinked
        locked, pid = is_profile_locked(tmp_dir)
        assert locked is False
        assert not os.path.exists(lock_path)


def test_verify_cdp_endpoint_when_closed():
    # An unused local port should immediately return available=False with instructions
    res = verify_cdp_endpoint("http://127.0.0.1:59222", timeout=0.5)
    assert res["available"] is False
    assert res["browser"] is None
    assert "google-chrome --remote-debugging-port=9222" in res["instructions"]
    assert res["error"] is not None


def test_connect_cdp_fail_closed():
    bt = BrowserTool()
    # Attempting to connect to an unreachable CDP port should return an error dict, not raise
    res = bt.connect_cdp("http://127.0.0.1:59222", timeout=1.0)
    assert res["status"] == "error"
    assert "CDP connection failed" in res["message"]
    assert "google-chrome --remote-debugging-port=9222" in res["instructions"]
    assert bt._session_mode == "none"
    assert bt.browser is None


def test_persistent_session_reuses_context():
    with tempfile.TemporaryDirectory() as tmp_dir:
        bt = BrowserTool()
        bt._persistent_profile_dir = tmp_dir

        # Open persistent browser headless
        res = bt.open_persistent_browser(url="about:blank", headless=True)
        assert res["status"] == "connected"
        assert bt._session_mode == "persistent_profile"
        assert bt.browser is not None
        assert bt.page is not None

        first_context = bt.context
        first_page = bt.page

        # Second navigation must reuse the exact same browser context and page
        bt.open_url("about:blank", headless=True)
        assert bt.context is first_context
        assert bt.page is first_page

        # DOM inspection must reuse the same session
        dom = bt.get_interactive_dom()
        assert isinstance(dom, str)
        assert bt.context is first_context

        # Disconnect preserves profile files on disk
        disc = bt.disconnect_session(preserve_data=True)
        assert disc["status"] == "disconnected"
        assert disc["data_preserved"] is True
        assert bt.browser is None
        assert os.path.exists(tmp_dir)


def test_open_authenticated_handles_locked_profile():
    with tempfile.TemporaryDirectory() as tmp_dir:
        current_pid = os.getpid()
        lock_path = os.path.join(tmp_dir, "SingletonLock")
        os.symlink(f"test-host-{current_pid}", lock_path)

        bt = BrowserTool()
        msg = bt.open_authenticated(url="about:blank", user_data_dir=tmp_dir, headless=True)
        assert "[PROFILE_LOCKED_ERROR]" in msg
        assert str(current_pid) in msg
        assert "--remote-debugging-port=9222" in msg


def test_accurate_authentication_state_evaluation():
    bt = BrowserTool()
    bt._ensure_session(headless=True)
    assert bt.page is not None

    # Load unauthenticated page fixture containing "Login / Signup"
    bt.page.goto("data:text/html,<html><body><header><h1>ReadXHub</h1><button data-lmms-id='7'>Login / Signup</button></header><main><p>Welcome to ReadXHub</p></main></body></html>")

    ctx = bt.get_account_context()
    auth = ctx.get("verified_website_authentication", {})
    assert auth.get("verified") is False
    assert auth.get("status") == "unverified"
    assert "visible login/sign-in options" in auth.get("reason", "")

    # Load authenticated page fixture containing user profile and logout CTA
    bt.page.goto("data:text/html,<html><body><header><h1>ReadXHub</h1><div class='user-profile' aria-label='User Profile'>@testuser</div><button>Log Out</button></header><main><p>Creator Dashboard</p></main></body></html>")

    ctx = bt.get_account_context()
    auth = ctx.get("verified_website_authentication", {})
    assert auth.get("verified") is True
    assert auth.get("status") == "verified"
    assert "Logout CTA or user profile element confirmed" in auth.get("evidence", "")

    bt.disconnect_session(preserve_data=True)


def test_get_chrome_executable_path():
    path = get_chrome_executable_path()
    assert path is not None
    assert os.path.exists(path)
    assert os.access(path, os.X_OK)
    assert "chrome" in path.lower() or "chromium" in path.lower()


def test_attach_existing_chrome_session_structure():
    bt = BrowserTool()
    # Test that attach_existing_chrome_session handles parameters and returns valid status
    with patch.object(bt, "connect_cdp", return_value={"status": "connected", "mode": "cdp"}):
        with patch("lmms.backend.tools.browser.verify_cdp_endpoint", return_value={"available": True}):
            res = bt.attach_existing_chrome_session(url="about:blank", cdp_endpoint="http://localhost:9222")
            assert res["status"] == "connected"
            assert res["mode"] == "cdp"

