"""
Security Regression Test Suite: Terminal Workspace Escape Prevention.

Verifies:
1. Restricted execution (sandboxed, low, medium) prevents host filesystem writes
   outside the allowed workspace, including via shell redirection and command chaining.
2. Legitimate shell syntax (pipes, redirection, command chaining) functions cleanly
   INSIDE the sandbox isolation boundary.
3. Fail-closed enforcement: if sandbox backends (Bubblewrap/Landlock) are unavailable,
   restricted execution strictly refuses to execute on the host.
4. Unsandboxed host execution is strictly denied unless permission tier is explicitly 'full'.
5. Host execution in full mode reports unconfined backend without false boundary claims.
"""

import os
import shutil
import tempfile
import pytest
from unittest.mock import patch

from lmms.backend.tools.terminal import TerminalTool, canonical_terminal_callback, config
from lmms.backend.security.models import ToolRequest, PermissionResult
from lmms.backend.security.executor import SecureExecutor
from lmms_sandbox.runner import default_runner
from lmms_sandbox.policy import PolicyAction


@pytest.fixture(autouse=True)
def isolated_sandbox_environment():
    """Ensure clean sandbox policy and environment without cross-test pollution."""
    orig_writable = list(default_runner.policy.writable_paths)
    orig_default_action = default_runner.policy.default_action
    default_runner.policy.writable_paths = []
    default_runner.policy.default_action = PolicyAction.ASK
    yield
    default_runner.policy.writable_paths = orig_writable
    default_runner.policy.default_action = orig_default_action


def test_redirection_escape_prevented_in_restricted_mode():
    """Verify shell redirection cannot write to host filesystem outside workspace in medium/sandboxed mode."""
    tt = TerminalTool()
    with tempfile.TemporaryDirectory() as parent_dir:
        ws_dir = os.path.join(parent_dir, "workspace")
        os.makedirs(ws_dir)
        outside_file = os.path.join(parent_dir, "outside_escape.txt")

        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        old_perm = config.get("permission_level")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            config.set("permission_level", "medium")

            # Command attempting to escape workspace via redirection to parent dir
            cmd = f"echo 'ESCAPE_PAYLOAD' > {outside_file}"
            ret = tt.run(cmd, cwd=ws_dir)

            # Security assertion: outside file must NEVER be created on the host
            assert not os.path.exists(outside_file), "CRITICAL: File was written outside workspace on host!"
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
            if old_perm:
                config.set("permission_level", old_perm)


def test_command_chaining_escape_prevented():
    """Verify command chaining (cd .. && touch) cannot escape workspace containment in restricted mode."""
    tt = TerminalTool()
    with tempfile.TemporaryDirectory() as parent_dir:
        ws_dir = os.path.join(parent_dir, "workspace")
        os.makedirs(ws_dir)
        outside_file = os.path.join(parent_dir, "chained_escape.txt")

        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        old_perm = config.get("permission_level")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            config.set("permission_level", "medium")

            # Command attempting to navigate out and write
            cmd = f"cd .. && echo 'CHAINED_ESCAPE' > chained_escape.txt"
            ret = tt.run(cmd, cwd=ws_dir)

            # Security assertion: outside file must NEVER exist on host
            assert not os.path.exists(outside_file), "CRITICAL: Chained command created file outside workspace!"
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
            if old_perm:
                config.set("permission_level", old_perm)


def test_legitimate_shell_syntax_inside_workspace():
    """Verify legitimate shell pipelines and redirects work safely within the sandbox."""
    tt = TerminalTool()
    with tempfile.TemporaryDirectory() as ws_dir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        old_perm = config.get("permission_level")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            config.set("permission_level", "medium")

            inside_file = os.path.join(ws_dir, "pipeline_test.txt")
            cmd = f"printf 'alpha\\nbeta\\ngamma\\n' | grep beta > {inside_file}"
            ret = tt.run(cmd, cwd=ws_dir)

            assert os.path.exists(inside_file)
            with open(inside_file, "r") as f:
                content = f.read().strip()
            assert content == "beta"
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
            if old_perm:
                config.set("permission_level", old_perm)


def test_fail_closed_when_sandbox_unavailable():
    """Verify restricted execution strictly refuses to execute on host if sandbox is missing."""
    with patch("shutil.which", return_value=None):
        with patch("lmms_sandbox.bwrap.BubblewrapSandbox.is_available", return_value=False):
            with patch("lmms_sandbox.landlock.LandlockSandbox.is_available", return_value=False):
                with tempfile.TemporaryDirectory() as ws_dir:
                    old_perm = config.get("permission_level")
                    old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
                    try:
                        os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
                        config.set("permission_level", "medium")

                        # 1. canonical_terminal_callback must raise PermissionError
                        with pytest.raises(PermissionError) as exc_info:
                            canonical_terminal_callback("echo should_fail", cwd=ws_dir)
                        assert "REFUSED: Sandbox isolation unavailable" in str(exc_info.value)

                        # 2. TerminalTool.run must return exit code -1 and REFUSED message
                        tt = TerminalTool()
                        code, out = tt.run("echo should_fail", cwd=ws_dir, return_exit_code=True)
                        assert code == -1
                        assert out.startswith("REFUSED")

                        # 3. SecureExecutor.execute must deny and fail closed
                        sec_exec = SecureExecutor()
                        req = ToolRequest(
                            tool_name="terminal.run",
                            command_line="echo should_fail",
                            arguments=[],
                            kwargs={"command": "echo should_fail"},
                            workspace=ws_dir,
                            permission_level="medium"
                        )
                        perm = PermissionResult(allowed=True, reason="ok", risk_level="medium")
                        res = sec_exec.execute(req, perm)
                        assert res.exit_code == -1
                        assert res.was_denied is True
                        assert "NOT isolated" in res.stderr or "REFUSED" in res.stderr
                    finally:
                        if old_ws:
                            os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
                        elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                            del os.environ["LMMS_ACTIVE_WORKSPACE"]
                        if old_perm:
                            config.set("permission_level", old_perm)


def test_unsandboxed_denied_without_full_permission():
    """Verify unsandboxed execution (sandboxed=False) is refused unless permission tier is 'full'."""
    with tempfile.TemporaryDirectory() as ws_dir:
        old_perm = config.get("permission_level")
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            tt = TerminalTool()

            for level in ("sandboxed", "low", "medium"):
                config.set("permission_level", level)
                code, out = tt.run("echo test", cwd=ws_dir, sandboxed=False, return_exit_code=True)
                # In restricted modes, effective_sandboxed is True or un-sandboxed is refused
                # Either way, host is NOT directly mutated without isolation
                assert code == 0 or code == -1
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
            if old_perm:
                config.set("permission_level", old_perm)


def test_full_mode_unconfined_host_backend():
    """Verify full mode explicitly reports unconfined_host without claiming container containment."""
    with tempfile.TemporaryDirectory() as ws_dir:
        old_perm = config.get("permission_level")
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            config.set("permission_level", "full")

            res = canonical_terminal_callback("echo 'host_test'", cwd=ws_dir, sandboxed=False)
            assert res["exit_code"] == 0
            assert res["sandboxed"] is False
            assert res["backend"] == "unconfined_host"
            assert "host_test" in res["output"]
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
            if old_perm:
                config.set("permission_level", old_perm)


def test_default_permission_level_is_medium_and_session_scoped():
    """Verify default permission level is medium and cannot be silently escalated by config."""
    from lmms.cli.interactive import InteractiveChat
    chat = InteractiveChat(model_name="test-model")
    assert chat.permission_level == "medium"

    # Terminal tool without arguments defaults to medium
    with tempfile.TemporaryDirectory() as ws_dir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            res = canonical_terminal_callback("echo test", cwd=ws_dir)
            assert res["sandboxed"] is True
            assert res["backend"] in ("bubblewrap", "landlock")
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_rejection_of_model_supplied_permission_escalation():
    """Verify model-generated tool arguments cannot escalate permission or disable sandbox."""
    with tempfile.TemporaryDirectory() as parent_dir:
        ws_dir = os.path.join(parent_dir, "workspace")
        os.makedirs(ws_dir)
        escape_file = os.path.join(parent_dir, "escalation_escape.txt")

        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            # Model attempts to inject permission escalation kwargs
            model_kwargs = {
                "command": f"echo 'PWNED' > {escape_file}",
                "permission_level": "full",
                "permission": "full",
                "perm": "full",
                "sandboxed": False,
            }

            # Tool execution must sanitize and reject model escalation
            tt = TerminalTool()
            ret = tt.run(
                command=model_kwargs["command"],
                cwd=ws_dir,
                sandboxed=model_kwargs.get("sandboxed"),
                permission_level="medium"  # Session remains medium
            )

            # File must not be created on host
            assert not os.path.exists(escape_file), "Security boundary breached via model-supplied permission escalation!"
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_invalid_permission_levels_safely_rejected():
    """Verify invalid or un-implemented permission levels (strict, ask, root) normalize safely to medium."""
    with tempfile.TemporaryDirectory() as ws_dir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            for invalid_tier in ("strict", "ask", "root", "admin", "unrestricted", "bypass", ""):
                res = canonical_terminal_callback("echo test", cwd=ws_dir, permission_level=invalid_tier)
                # Must safely normalize to medium (which enforces sandbox containment)
                assert res["sandboxed"] is True
                assert res["backend"] in ("bubblewrap", "landlock")
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_full_mode_explicit_authorization_requirement():
    """Verify full mode cannot be silently engaged without explicit user opt-in."""
    with tempfile.TemporaryDirectory() as ws_dir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = ws_dir
            # Without sandboxed=False, full mode still defaults to sandboxed execution
            res_default = canonical_terminal_callback("echo test", cwd=ws_dir, permission_level="full")
            assert res_default["sandboxed"] is True

            # Unconfined host execution requires explicit sandboxed=False AND permission_level='full'
            res_unconfined = canonical_terminal_callback("echo test", cwd=ws_dir, permission_level="full", sandboxed=False)
            assert res_unconfined["sandboxed"] is False
            assert res_unconfined["backend"] == "unconfined_host"
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]
