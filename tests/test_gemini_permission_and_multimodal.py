"""
Regression and verification suite for:
1. Gemini-style interactive permission prompt and prefix allowlisting.
2. 3-tier permission manager enforcement (low, medium, full).
3. Sandbox runner execution with confirm_callback (no NameError: sys).
4. Browser observe_page *args, **kwargs compatibility.
"""

import os
import json
import pytest
from lmms.cli.permission_prompt import (
    PermissionAction,
    extract_base_command_prefix,
    is_command_always_allowed,
    save_persistent_allowed_prefix,
    _SESSION_ALLOWED_PREFIXES,
    ask_permission_interactive
)
from lmms.backend.security.models import ToolRequest
from lmms.backend.security.permission_manager import permission_manager
from lmms_sandbox.runner import default_runner


def test_extract_base_command_prefix():
    assert extract_base_command_prefix("git status -s") == "git status"
    assert extract_base_command_prefix("git diff HEAD~1") == "git diff"
    assert extract_base_command_prefix("git log -n 5") == "git log"
    assert extract_base_command_prefix("npm test --watch") == "npm test"
    assert extract_base_command_prefix("npm run build") == "npm run"
    assert extract_base_command_prefix("du -sh Projects") == "du"
    assert extract_base_command_prefix("ls -la /tmp") == "ls"
    assert extract_base_command_prefix("cat README.md") == "cat"


def test_session_always_allow_prefix():
    _SESSION_ALLOWED_PREFIXES.clear()
    assert not is_command_always_allowed("git status -s")
    
    _SESSION_ALLOWED_PREFIXES.add("git status")
    assert is_command_always_allowed("git status")
    assert is_command_always_allowed("git status -s")
    assert is_command_always_allowed("git status --porcelain")
    assert not is_command_always_allowed("git commit -m 'foo'")
    _SESSION_ALLOWED_PREFIXES.clear()


def test_permission_tier_low_requires_confirmation():
    _SESSION_ALLOWED_PREFIXES.clear()
    req = ToolRequest(
        tool_name="terminal.run",
        command_line="ls -la",
        arguments=[],
        kwargs={"command": "ls -la"},
        workspace="/home/kali/Projects/LMMs",
        permission_level="low"
    )
    res = permission_manager.check_permission(req)
    assert res.allowed is True
    assert res.requires_confirmation is True


def test_permission_tier_medium_inside_workspace():
    _SESSION_ALLOWED_PREFIXES.clear()
    req = ToolRequest(
        tool_name="terminal.run",
        command_line="git status",
        arguments=[],
        kwargs={"command": "git status"},
        workspace="/home/kali/Projects/LMMs",
        permission_level="medium"
    )
    res = permission_manager.check_permission(req)
    assert res.allowed is True
    assert res.requires_confirmation is False


def test_permission_tier_medium_outside_workspace():
    _SESSION_ALLOWED_PREFIXES.clear()
    req = ToolRequest(
        tool_name="terminal.run",
        command_line="cat /etc/passwd",
        arguments=[],
        kwargs={"command": "cat /etc/passwd"},
        workspace="/home/kali/Projects/LMMs",
        permission_level="medium"
    )
    res = permission_manager.check_permission(req)
    assert res.allowed is True
    assert res.requires_confirmation is True


def test_permission_tier_full_allows_standard_command():
    _SESSION_ALLOWED_PREFIXES.clear()
    req = ToolRequest(
        tool_name="terminal.run",
        command_line="du -sh /home/kali",
        arguments=[],
        kwargs={"command": "du -sh /home/kali"},
        workspace="/home/kali/Projects/LMMs",
        permission_level="full"
    )
    res = permission_manager.check_permission(req)
    assert res.allowed is True
    assert res.requires_confirmation is False


def test_permission_tier_full_blocks_or_confirms_destructive():
    _SESSION_ALLOWED_PREFIXES.clear()
    req = ToolRequest(
        tool_name="terminal.run",
        command_line="rm -rf /",
        arguments=[],
        kwargs={"command": "rm -rf /"},
        workspace="/home/kali/Projects/LMMs",
        permission_level="full"
    )
    res = permission_manager.check_permission(req)
    # Either blocked by policy or requires explicit confirmation
    assert res.allowed is False or res.requires_confirmation is True


def test_sandbox_runner_confirm_callback_no_sys_name_error():
    # Verify that default_runner.run with confirm_callback runs du or ls without NameError: sys
    res = default_runner.run(
        "ls",
        workspace_dir="/home/kali/Projects/LMMs",
        enforce_sandbox=True,
        confirm_callback=lambda cmd, r: True
    )
    assert res.exit_code == 0
    assert "README.md" in res.stdout or res.success


def test_observe_page_handler_with_extra_kwargs():
    from lmms.backend.orchestration.executor import UnifiedToolExecutor
    from lmms.backend.orchestration.registry import ToolRegistry
    
    registry = ToolRegistry()
    executor = UnifiedToolExecutor(registry)
    # Register our handler with extra kwargs
    executor.register_handler("browser.observe_page", lambda url=None, **kw: {"status": "ok", "url": url, "extra": kw})
    res = executor.execute("browser.observe_page", {"url": "https://example.com", "inspect_forms": True})
    assert res.success is True
    assert res.data["url"] == "https://example.com"
    assert res.data["extra"]["inspect_forms"] is True


def test_ask_browser_profile_interactive_selection(monkeypatch):
    from lmms.cli.permission_prompt import ask_browser_profile_interactive
    import io
    
    profiles = {
        "Chrome_Default (markanm.official@gmail.com)": {"base_path": "/home/kali/.config/google-chrome", "dir_name": "Default"},
        "Chrome_Profile 1 (mr.rajsingh18110@gmail.com)": {"base_path": "/home/kali/.config/google-chrome", "dir_name": "Profile 1"}
    }
    # Mock user typing '2' (selecting Profile 1)
    monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
    chosen = ask_browser_profile_interactive(profiles)
    assert chosen is not None
    assert chosen["dir_name"] == "Profile 1"


def test_ask_browser_profile_interactive_cancel(monkeypatch):
    from lmms.cli.permission_prompt import ask_browser_profile_interactive
    import io
    
    profiles = {
        "Chrome_Default (markanm.official@gmail.com)": {"base_path": "/home/kali/.config/google-chrome", "dir_name": "Default"},
    }
    # Mock user typing '2' (Cancel option)
    monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
    chosen = ask_browser_profile_interactive(profiles)
    assert chosen is None


def test_browser_profiles_local_state_extraction():
    from lmms.backend.tools.browser import browser_tool
    profiles = browser_tool.get_browser_profiles()
    assert isinstance(profiles, dict)
    # Check that at least some profile display names contain extracted emails
    emails_found = [k for k in profiles.keys() if "@" in k]
    assert len(emails_found) > 0


def test_permission_result_tuple_and_command():
    from lmms.cli.permission_prompt import PermissionResult, PermissionAction
    res = PermissionResult(PermissionAction.ALLOW_ONCE, "git status", "git status --porcelain")
    # Verify tuple unpacking compatibility
    action, prefix = res
    assert action == PermissionAction.ALLOW_ONCE
    assert prefix == "git status"
    assert res.command == "git status --porcelain"
    assert len(res) == 2


def test_robust_parse_tool_call_nemotron_xml_formats():
    from lmms.backend.main import robust_parse_tool_call
    
    # Format 1: Nemotron syntax with tool="..." and <parameter>key>value</parameter>
    raw1 = """<tool_call>
<tool_call><function_call>="terminal.run" tool="terminal.run"><parameter>command>du -sh /home/kali/Projects 2>/dev/null || echo "Folder not found or inaccessible"</parameter></function_call>
<tool_call>"""
    p1 = robust_parse_tool_call(raw1)
    assert p1["tool"] == "terminal.run"
    assert "du -sh /home/kali/Projects" in p1["kwargs"]["command"]

    # Format 2: Nemotron syntax without tool="..." attribute
    raw2 = """<function_call>="terminal.run"><parameter>command>uptime</parameter></function_call>"""
    p2 = robust_parse_tool_call(raw2)
    assert p2["tool"] == "terminal.run"
    assert p2["kwargs"]["command"] == "uptime"

    # Format 3: Direct XML parameter tags
    raw3 = """<function=files.list><path>/home/kali</path></function>"""
    p3 = robust_parse_tool_call(raw3)
    assert p3["tool"] == "files.list"
    assert p3["kwargs"]["path"] == "/home/kali"

    # Format 4: OpenAI JSON tool call inside tool_call
    raw4 = """<tool_call>{"name": "browser.open_url", "arguments": {"url": "https://readxhub.in"}}</tool_call>"""
    p4 = robust_parse_tool_call(raw4)
    assert p4["tool"] == "browser.open_url"
    assert p4["kwargs"]["url"] == "https://readxhub.in"


def test_browser_stealth_and_local_file_support():
    from lmms.backend.tools.browser import STEALTH_INIT_SCRIPT, inject_universal_stealth
    assert "navigator" in STEALTH_INIT_SCRIPT
    assert "webdriver" in STEALTH_INIT_SCRIPT
    assert "window.chrome" in STEALTH_INIT_SCRIPT

    # Verify dummy object can receive stealth injection without crashing
    class DummyTarget:
        def __init__(self):
            self.scripts = []
        def add_init_script(self, s):
            self.scripts.append(s)
        def evaluate(self, s):
            pass

    dummy = DummyTarget()
    inject_universal_stealth(dummy)
    assert len(dummy.scripts) > 0


def test_should_force_tool_mode_substring_isolation():
    from lmms.backend.main import should_force_tool_mode
    # Test query that has 'which' (must NOT be treated as 'hi')
    assert should_force_tool_mode("run html  file which is in the folder") is True
    assert should_force_tool_mode("open html file which is in the folder") is True
    assert should_force_tool_mode("run command") is True
    # Pure greetings
    assert should_force_tool_mode("hello") is False
    assert should_force_tool_mode("hi") is False
    assert should_force_tool_mode("hey") is False
    assert should_force_tool_mode("how are you") is False


def test_browser_unsupported_flag_removed():
    import inspect
    from lmms.backend.tools.browser import BrowserTool
    source = inspect.getsource(BrowserTool)
    assert "--disable-blink-features=AutomationControlled" not in source
    assert "--test-type" in source


def test_arrow_key_detection():
    from lmms.cli.permission_prompt import _is_up_key, _is_down_key
    # Normal ANSI mode
    assert _is_up_key("\x1b[A") is True
    assert _is_down_key("\x1b[B") is True
    # Application cursor keys (SS3 mode)
    assert _is_up_key("\x1bOA") is True
    assert _is_down_key("\x1bOB") is True
    # Vim keys
    assert _is_up_key("k") is True
    assert _is_down_key("j") is True


def test_cli_installer_lightweight_engine_mapping():
    from lmms.cli.installer import CLIInstaller, ENGINE1_PACKAGES, CLI_PACKAGES
    installer = CLIInstaller(["--cli"])
    assert "cli" in installer.selected_components
    assert "engine1" in installer.selected_components
    assert "engine2" not in installer.selected_components

    # Verify Engine 1 has llama-cpp-python and no torch/transformers bloat
    specs1 = [p["spec"] for p in ENGINE1_PACKAGES]
    assert "llama-cpp-python" in specs1
    assert "transformers" not in specs1
    assert "sentence-transformers" not in specs1
    assert "torch" not in specs1

    # Verify CLI packages include PyQt6 and qasync for /addmodel dialog
    cli_specs = [p["spec"] for p in CLI_PACKAGES]
    assert "PyQt6" in cli_specs
    assert "qasync" in cli_specs


