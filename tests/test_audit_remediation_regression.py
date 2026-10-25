"""
Regression tests verifying remediation of findings from COPILOT_TERMINAL_FILE_EXECUTION_AUDIT:
1. Blocked commands return specific, actionable denial reasons with safe next steps.
2. Legitimate workspace file writes return verified success.
3. Failed or denied writes are never reported as successful.
4. Malformed message.send calls return clear schema validation errors while preserving aliases.
5. Core shell security checks (sudo, eval, pipelines, subshells) remain strictly enforced.
"""

import os
import tempfile
import pytest

from lmms.backend.security.command_parser import parse_shell_command, CommandParserError
from lmms.backend.security.models import ToolRequest, PermissionResult
from lmms.backend.security.permission_manager import permission_manager
from lmms.backend.security.executor import SecureExecutor
from lmms.backend.tools.files import FileTool, canonical_file_write
from lmms.backend.orchestration.executor import UnifiedToolExecutor
from lmms.backend.orchestration.registry import ToolRegistry


def test_blocked_chained_command_returns_specific_actionable_reason():
    """Verify chaining with '&&' returns an explicit construct name and remedy."""
    cmd = "cd /home/kali && ls -la"
    with pytest.raises(CommandParserError) as exc_info:
        parse_shell_command(cmd)

    err = exc_info.value
    assert "logical AND chaining ('&&')" in str(err)
    assert "Remedy:" in str(err)
    assert hasattr(err, "remedy")
    assert "Execute commands sequentially as separate, individual tool calls" in err.remedy

    # Also test via permission_manager
    req = ToolRequest(
        tool_name="terminal.run",
        command_line=cmd,
        arguments=[],
        kwargs={"command": cmd},
        workspace="/home/kali/Projects/LMMs",
        permission_level="medium"
    )
    perm = permission_manager.check_permission(req)
    assert perm.allowed is False
    assert "logical AND chaining ('&&')" in perm.reason
    assert "Remedy:" in perm.reason


def test_dangerous_shell_constructs_remain_strictly_blocked():
    """Verify privilege escalation, subshells, pipelines, and evaluation remain blocked."""
    test_cases = [
        ("sudo apt install bwrap", "privilege escalation ('sudo')", "without sudo"),
        ("cat /etc/passwd | grep root", "shell pipeline ('|')", "piping"),
        ("echo $(whoami)", "subshell command substitution ('$()')", "separate step"),
        ("echo `id`", "backtick command substitution ('`')", "separate step"),
        ("eval 'rm -rf /'", "dynamic code evaluation ('eval')", "without eval"),
        ("bash -c 'ls'", "nested shell invocation ('bash')", "without invoking bash"),
        ("echo payload > outside.txt", "output redirection ('>')", "files.write"),
    ]

    for cmd, expected_construct, expected_remedy in test_cases:
        with pytest.raises(CommandParserError) as exc_info:
            parse_shell_command(cmd)
        err = exc_info.value
        assert expected_construct in str(err), f"Expected {expected_construct} in error for command: {cmd}"
        assert expected_remedy in str(err), f"Expected {expected_remedy} in remedy for command: {cmd}"


def test_legitimate_workspace_file_write_returns_verified_success():
    """Legitimate workspace writes physically persist content and return verified success."""
    ft = FileTool()
    reg = ToolRegistry()
    orch_exec = UnifiedToolExecutor(reg)

    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            target = os.path.join(tmpdir, "verified_document.txt")
            payload = "Grounded file content verified with sha256."

            # 1. Direct FileTool verification
            res = ft.write(target, payload)
            assert "[FILE_WRITE_VERIFIED]" in res
            assert os.path.exists(target)
            with open(target, "r", encoding="utf-8") as f:
                assert f.read() == payload

            # 2. Orchestration executor verification
            target_orch = os.path.join(tmpdir, "orch_document.txt")
            exec_res = orch_exec.execute("files.write", {"path": target_orch, "content": payload})
            assert exec_res.success is True
            assert "[FILE_WRITE_VERIFIED]" in str(exec_res.data)
            assert os.path.exists(target_orch)
            with open(target_orch, "r", encoding="utf-8") as f:
                assert f.read() == payload

            # 3. Canonical write verification
            target_canon = os.path.join(tmpdir, "canon_document.txt")
            c_res = canonical_file_write(target_canon, payload)
            assert c_res["status"] == "success"
            assert c_res["verified"] is True
            assert os.path.exists(target_canon)
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_failed_or_denied_writes_never_reported_as_successful():
    """Writing outside the workspace boundary fails and is never marked as a success."""
    ft = FileTool()
    reg = ToolRegistry()
    orch_exec = UnifiedToolExecutor(reg)

    with tempfile.TemporaryDirectory() as tmpdir:
        old_ws = os.environ.get("LMMS_ACTIVE_WORKSPACE")
        try:
            os.environ["LMMS_ACTIVE_WORKSPACE"] = tmpdir
            # Attempt to write outside workspace
            outside_target = os.path.abspath(os.path.join(tmpdir, "..", "forbidden_outside.txt"))

            # 1. FileTool write outside workspace
            res = ft.write(outside_target, "forbidden payload")
            assert "[FILE_WRITE_ERROR]" in res
            assert "Workspace boundary violation" in res
            assert not os.path.exists(outside_target)

            # 2. Orchestration executor MUST report success=False
            exec_res = orch_exec.execute("files.write", {"path": outside_target, "content": "forbidden payload"})
            assert exec_res.success is False
            assert "boundary" in exec_res.error.lower()
            assert "[EXECUTION_FAILED]" in exec_res.formatted_observation
            assert "[FILE_WRITE_ERROR]" in exec_res.formatted_observation
            assert not os.path.exists(outside_target)

            # 3. Canonical write outside workspace
            c_res = canonical_file_write(outside_target, "forbidden payload")
            assert c_res["status"] == "error"
            assert c_res["verified"] is False
            assert "Boundary violation" in c_res["error"]
            assert not os.path.exists(outside_target)
        finally:
            if old_ws:
                os.environ["LMMS_ACTIVE_WORKSPACE"] = old_ws
            elif "LMMS_ACTIVE_WORKSPACE" in os.environ:
                del os.environ["LMMS_ACTIVE_WORKSPACE"]


def test_malformed_message_send_calls_return_clear_validation_errors():
    """Verify schema validation for message.send: required fields, types, and alias support."""
    reg = ToolRegistry()
    orch_exec = UnifiedToolExecutor(reg)

    # 1. Empty kwargs: missing 'message'
    res_empty = orch_exec.execute("message.send", {})
    assert res_empty.success is False
    assert "Missing required parameter 'message'" in res_empty.error
    assert "[VALIDATION_ERROR]" in res_empty.formatted_observation

    # 2. Missing 'message' with only recipient
    res_no_msg = orch_exec.execute("message.send", {"recipient": "admin"})
    assert res_no_msg.success is False
    assert "Missing required parameter 'message'" in res_no_msg.error

    # 3. Invalid type: message passed as integer
    res_wrong_type = orch_exec.execute("message.send", {"message": 98765})
    assert res_wrong_type.success is False
    assert "Parameter 'message' must be a string" in res_wrong_type.error

    # 4. Valid alias 'text' normalized to 'message'
    # Should pass argument validation cleanly
    tool_def = reg.get("message.send")
    clean_name, clean_args = orch_exec.normalize_call("message.send", {"text": "Hello via text alias", "recipient": "Alert"})
    is_valid, err = orch_exec.validate_arguments(tool_def, clean_args)
    assert is_valid is True
    assert clean_args["message"] == "Hello via text alias"
    assert clean_args["recipient"] == "Alert"


def test_secure_executor_denial_includes_actionable_stderr():
    """Verify SecureExecutor.execute populates stderr with structured denial reason."""
    sec_exec = SecureExecutor()
    cmd = "echo alpha && echo beta"
    req = ToolRequest(
        tool_name="terminal.run",
        command_line=cmd,
        arguments=[],
        kwargs={"command": cmd},
        workspace="/tmp",
        permission_level="medium"
    )
    perm = permission_manager.check_permission(req)
    assert perm.allowed is False

    res = sec_exec.execute(req, perm)
    assert res.exit_code == 1
    assert res.was_denied is True
    assert "[TOOL_DENIED]" in res.stderr
    assert "logical AND chaining ('&&')" in res.stderr
    assert "The command was NOT executed on the host" in res.stderr
