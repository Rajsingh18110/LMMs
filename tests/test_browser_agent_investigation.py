"""
Regression test suite for browser agent investigation, DOM automation,
account context, companion tool bundling, and shell execution fixes.
"""

import os
import pytest
from lmms.backend.orchestration.router import IntentRouter, IntentType
from lmms.backend.orchestration.registry import ToolRegistry
from lmms.backend.orchestration.selector import ToolSelector
from lmms.backend.tools.browser import BrowserTool
from lmms.backend.tools.terminal import TerminalTool
from lmms.backend.cli.timeline import TimelineRenderer, extract_domain_pills


def test_tld_routing_readxhub_in():
    """Verify that domains with .in, .ai, .co, .dev route cleanly to BROWSER_AUTOMATION."""
    router = IntentRouter()
    
    # The incident prompt
    res = router.route("open readxhub.in and inspect the site")
    assert res.intent == IntentType.BROWSER_AUTOMATION
    assert res.requires_tools is True
    assert "browser" in res.suggested_categories

    # Other non-standard TLDs
    res_ai = router.route("open anthropic.ai and check documentation")
    assert res_ai.intent == IntentType.BROWSER_AUTOMATION

    res_dev = router.route("visit web-toolbox.dev and check tools")
    assert res_dev.intent == IntentType.BROWSER_AUTOMATION


def test_multi_capability_routing_with_blog_and_account():
    """Verify that multi-step prompt routing suggests browser, files, and system tools."""
    router = IntentRouter()
    prompt = "open readxhub.in, inspect the site, write a detailed blog about LMMs using my email and account context"
    res = router.route(prompt)
    assert res.intent == IntentType.BROWSER_AUTOMATION
    assert "browser" in res.suggested_categories
    assert "files" in res.suggested_categories
    assert "system" in res.suggested_categories


def test_companion_tool_bundling_on_discovery():
    """Verify that discovering browser.open_url automatically bundles DOM companion tools."""
    registry = ToolRegistry()
    selector = ToolSelector(registry)
    
    # Initial empty or file-only selection
    dummy_intent = router = IntentRouter().route("ls files")
    sel_res = selector.select(dummy_intent, current_workspace="/home/kali")
    assert "browser.open_url" not in sel_res.selected_ids
    assert "browser.click_element" not in sel_res.selected_ids

    # Dynamic discovery of browser.open_url
    updated_sel = selector.discover_additional_tool(sel_res, "browser.open_url")
    assert "browser.open_url" in updated_sel.selected_ids
    # Crucial fix verification: companions must be bundled!
    assert "browser.click_element" in updated_sel.selected_ids
    assert "browser.fill_form" in updated_sel.selected_ids
    assert "browser.get_interactive_dom" in updated_sel.selected_ids


def test_account_context_retrieval_safe():
    """Verify that get_account_context() executes safely without exposing passwords or keys."""
    bt = BrowserTool()
    acc_ctx = bt.get_account_context()
    assert isinstance(acc_ctx, dict)
    assert acc_ctx.get("status") == "success"
    assert "primary_email" in acc_ctx
    assert "git_email" in acc_ctx
    assert "git_user" in acc_ctx
    assert "browser_accounts" in acc_ctx

    # Security check: verify no secrets or passwords in account info
    for acc in acc_ctx.get("browser_accounts", []):
        assert "password" not in acc
        assert "cookie" not in acc
        assert "token" not in acc


def test_terminal_shell_redirection():
    """Verify that commands using shell operators like '>' execute cleanly within workspace boundary."""
    from lmms.backend.tools.terminal import config
    tt = TerminalTool()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        old_perm = config.get("permission_level")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            test_file = os.path.join(tmpdir, "test_output.txt")
            cmd = f"echo 'Hello LMMs' > {test_file}"

            # 1. Test sandboxed execution inside workspace
            config.set("permission_level", "medium")
            res = tt.run(cmd, cwd=tmpdir, sandboxed=True)
            assert os.path.exists(test_file)
            with open(test_file, "r") as f:
                assert f.read().strip() == "Hello LMMs"

            # 2. Test full mode host execution
            os.remove(test_file)
            config.set("permission_level", "full")
            res2 = tt.run(cmd, cwd=tmpdir, sandboxed=False)
            assert os.path.exists(test_file)
            with open(test_file, "r") as f:
                assert f.read().strip() == "Hello LMMs"
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
            if old_perm:
                config.set("permission_level", old_perm)


def test_timeline_dom_click_and_account_nodes():
    """Verify timeline rendering handles click_element, fill_form, and account identity."""
    renderer = TimelineRenderer()
    renderer.start_turn("test turn", model_name="test-model")

    # Click element
    call_str = renderer.emit_tool_call("browser.click_element", {"selector": "7", "id": 7})
    assert "Clicking" in call_str
    assert "'7'" in call_str

    obs_str = renderer.emit_observation("browser.click_element", "[CLICK_SUCCESS] Clicked '7'. [NAVIGATED -> https://auth.readxhub.in/login]")
    assert "navigated to" in obs_str

    # Account identity
    call_id = renderer.emit_tool_call("account.get_current_identity", {})
    assert "Checking Account Identity" in call_id

    obs_id = renderer.emit_observation("account.get_current_identity", '{"primary_email": "test@example.com"}')
    assert "test@example.com" in obs_id


def test_account_context_four_tier_and_unavailable_fallback(monkeypatch):
    """Verify that get_account_context returns structured 4-tier identity and falls back to 'unavailable' when empty."""
    bt = BrowserTool()

    # 1. Normal state with real environment
    ctx = bt.get_account_context()
    assert "configured_identity" in ctx
    assert "browser_profiles" in ctx
    assert "website_authentication" in ctx
    assert ctx["status"] in ("success", "unavailable")

    # 2. Mock state with zero identity anywhere
    monkeypatch.setattr(bt, "get_browser_profiles", lambda: {})
    import subprocess
    def mock_run(*args, **kwargs):
        class Res:
            returncode = 1
            stdout = ""
        return Res()
    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.delenv("USER_EMAIL", raising=False)
    monkeypatch.delenv("GIT_AUTHOR_EMAIL", raising=False)

    empty_ctx = bt.get_account_context()
    assert empty_ctx["status"] == "unavailable"
    assert empty_ctx["primary_email"] == ""
    assert "reason" in empty_ctx
    assert "No configured user identity found" in empty_ctx["reason"]


def test_file_write_read_back_verification_and_success():
    """Verify that file writing performs read-back verification and returns structured metadata."""
    import tempfile
    from lmms.backend.tools.files import FileTool, canonical_file_write

    ft = FileTool()
    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            target = os.path.join(tmpdir, "verified_blog.md")
            test_content = "# LMMs Architecture\n\nA high-performance local AI studio.\nLine 3 of verified blog.\n"

            # 1. FileTool.write verification
            res = ft.write(target, test_content)
            assert "[FILE_WRITE_VERIFIED]" in res
            assert "Successfully wrote and verified" in res
            assert f"{len(test_content.splitlines())} lines" in res
            assert f"{len(test_content)} chars" in res
            assert f"{len(test_content.encode('utf-8'))} bytes" in res

            # Verify actual file on disk
            with open(target, "r", encoding="utf-8") as f:
                disk_content = f.read()
            assert disk_content == test_content

            # 2. canonical_file_write verification
            target_py = os.path.join(tmpdir, "test_code.py")
            py_code = "def hello():\n    return 'world'\n"
            c_res = canonical_file_write(target_py, py_code)
            assert c_res["status"] == "success"
            assert c_res["verified"] is True
            assert c_res["lines"] == 2
            assert c_res["chars"] == len(py_code)
            assert c_res["bytes"] == len(py_code.encode("utf-8"))
            assert "sha256" in c_res
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_file_write_integrity_mismatch_detection(monkeypatch):
    """Verify that read-back integrity mismatch triggers bounded retry and failure report."""
    import tempfile
    from lmms.backend.tools.files import _write_and_verify

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "corrupted.txt")

        # Mock read-back to simulate disk write truncation or hardware fault
        import builtins
        orig_open = builtins.open
        def mock_open(file, mode="r", *args, **kwargs):
            if "r" in mode and str(file) == str(test_file):
                # Return corrupted truncated content
                import io
                return io.StringIO("partial truncated")
            return orig_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)
        success, msg, stats = _write_and_verify(test_file, "full complete content here", max_retries=1)
        assert success is False
        assert "FILE_WRITE_INTEGRITY_ERROR" in msg
        assert "Read-back verification failed" in msg


def test_selector_bundles_account_companion_tools():
    """Verify that discovering account/identity capabilities bundles account.get_current_identity."""
    registry = ToolRegistry()
    selector = ToolSelector(registry)
    dummy_intent = IntentRouter().route("ls files")
    sel_res = selector.select(dummy_intent, current_workspace="/home/kali")

    # Discovering by 'identity' keyword
    updated = selector.discover_additional_tool(sel_res, "identity")
    assert "account.get_current_identity" in updated.selected_ids

    # Discovering by 'email' keyword
    updated2 = selector.discover_additional_tool(sel_res, "user_email")
    assert "account.get_current_identity" in updated2.selected_ids


def test_browser_404_anti_loop_recovery_mock(monkeypatch):
    """Verify that BrowserTool automatically recovers to site root on repeated 404s without looping."""
    bt = BrowserTool()

    # Mock page and browser
    class MockPage:
        def __init__(self):
            self._url = "https://example.com/initial"
        @property
        def url(self):
            return self._url
        def title(self):
            if self._url == "https://example.com":
                return "Homepage"
            return "404 Not Found"
        def evaluate(self, script):
            if "document.body.innerText" in script or "innerText" in script:
                if self._url == "https://example.com":
                    return "Welcome to Homepage"
                return "404: This page could not be found."
            return {"title": "Homepage", "url": "https://example.com", "elements": [{"id": 1, "tag": "a", "type": "", "name": "", "href": "/about", "placeholder": "", "label": "About", "selector": "[data-lmms-id='1']"}]}
        def wait_for_timeout(self, ms):
            pass
        def goto(self, url, **kwargs):
            self._url = url

    mock_p = MockPage()
    monkeypatch.setattr(bt, "_ensure_session", lambda *a, **k: None)
    monkeypatch.setattr(bt, "_goto_if_needed", lambda u: None)
    bt.page = mock_p

    # First 404: Returns 404 advice with site root
    res1 = bt.open_url("https://example.com/bad-path-1")
    assert "[HTTP 404 / Page Not Found]" in res1
    assert "https://example.com" in res1
    assert bt._domain_404_counts["example.com"] == 1

    # Second 404 on same domain: Auto-recovers to site root
    res2 = bt.open_url("https://example.com/bad-path-2")
    assert "[HTTP 404 / REPEATED NAVIGATION FAILURE DETECTED]" in res2
    assert "Automatic recovery engaged: Navigated back to site root 'https://example.com'" in res2
    assert mock_p.url == "https://example.com"


def test_interactive_dom_extracts_href_and_attributes(monkeypatch):
    """Verify that get_interactive_dom formats href, action, and input value attributes."""
    bt = BrowserTool()

    class MockPage:
        def __init__(self):
            self.url = "https://readxhub.in"
        def evaluate(self, script):
            if "document.body.innerText" in script:
                return "Welcome to ReadXHub"
            return {
                "title": "ReadXHub Home",
                "url": "https://readxhub.in",
                "elements": [
                    {
                        "id": 1,
                        "tag": "a",
                        "type": "",
                        "name": "",
                        "href": "/explore",
                        "action": "",
                        "value": "",
                        "placeholder": "",
                        "label": "Explore Blogs",
                        "selector": "[data-lmms-id='1']"
                    },
                    {
                        "id": 2,
                        "tag": "input",
                        "type": "text",
                        "name": "search",
                        "href": "",
                        "action": "/search",
                        "value": "AI Studios",
                        "placeholder": "Search topics...",
                        "label": "Search topics...",
                        "selector": "input[name='search']"
                    }
                ]
            }
        def wait_for_timeout(self, ms):
            pass

    bt.page = MockPage()
    monkeypatch.setattr(bt, "_ensure_session", lambda *a, **k: None)

    dom_res = bt.get_interactive_dom()
    assert "[ID 1] <a href='/explore'" in dom_res
    assert "label='Explore Blogs'" in dom_res
    assert "[ID 2] <input" in dom_res
    assert "action='/search'" in dom_res
    assert "value='AI Studios'" in dom_res
    assert "placeholder='Search topics...'" in dom_res
