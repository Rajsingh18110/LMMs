"""
Regression test suite for Orchestrator-Level Completion Guard.
Verifies that denied, failed, or unverified tool operations can never be represented
as verified successes in final agent responses or internal state, while ensuring
legitimate retries, partial completions, and unrelated informational responses work properly.
"""

import os
import tempfile
import pytest

from lmms.backend.orchestration.completion_guard import (
    CompletionGuard,
    ToolExecutionStatus,
    extract_target_from_call,
)
from lmms.backend.orchestration.registry import ToolRegistry, DynamicToolDefinition, ToolMetadata
from lmms.backend.orchestration.executor import UnifiedToolExecutor
from lmms.backend.orchestration.pipeline import OrchestrationPipeline


def test_scenario_1_denied_tool_call_followed_by_false_success_claim():
    """
    Scenario 1:
    A tool call is denied by security policy. The model attempts to claim
    'I have created index.html at /home/kali/development/index.html'.
    The completion guard MUST intercept the response and replace it with an
    honest, authoritative notice stating the file was NOT created.
    """
    guard = CompletionGuard()
    guard.start_turn()

    target_path = "/home/kali/development/index.html"
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": target_path, "content": "<html>Hello</html>"},
        status=ToolExecutionStatus.DENIED,
        verified=False,
        reason_or_error="Target path is outside the allowed workspace boundary ('/tmp/workspace').",
        output_snippet=""
    )

    hallucinated_reply = f"I have successfully created index.html at {target_path} with the required HTML structure."
    guarded_reply, res = guard.validate_and_guard(hallucinated_reply, workspace="/tmp/workspace")

    assert res.is_valid is False
    assert res.correction_applied is True
    assert len(res.false_claims_detected) > 0
    assert "Operation Not Completed" in guarded_reply
    assert "files.write" in guarded_reply
    assert "index.html" in guarded_reply
    assert "outside the allowed workspace boundary" in guarded_reply
    assert "was **NOT** completed on the host" in guarded_reply
    assert "I have successfully created" not in guarded_reply


def test_scenario_2_failed_file_write_followed_by_false_success_claim():
    """
    Scenario 2:
    A file write fails (e.g. disk error, permission error, boundary violation).
    The model asserts that it wrote the file.
    The guard intercepts and prevents the false claim.
    """
    guard = CompletionGuard()
    guard.start_turn()

    target_path = "/var/log/custom.log"
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": target_path, "content": "log data"},
        status=ToolExecutionStatus.FAILED,
        verified=False,
        reason_or_error="Permission denied: [Errno 13] Permission denied: '/var/log/custom.log'",
        output_snippet=""
    )

    hallucinated_reply = "I wrote the file custom.log with the logging configuration."
    guarded_reply, res = guard.validate_and_guard(hallucinated_reply, workspace="/home/kali/Projects")

    assert res.is_valid is False
    assert res.correction_applied is True
    assert "Operation Not Completed" in guarded_reply
    assert "custom.log" in guarded_reply
    assert "was **NOT** completed on the host" in guarded_reply


def test_scenario_3_unverified_result_must_not_count_as_success():
    """
    Scenario 3:
    An operation is triggered (e.g. browser.save_draft), but verification is unconfirmed/false.
    The model cannot claim verified success.
    """
    guard = CompletionGuard()
    guard.start_turn()

    guard.record_operation(
        tool_name="browser.save_draft",
        kwargs={"title": "My Post", "content": "Body text"},
        status=ToolExecutionStatus.UNVERIFIED,
        verified=False,
        reason_or_error="Draft save button clicked but save confirmation toast did not appear.",
        output_snippet=""
    )

    hallucinated_reply = "I have successfully saved your draft post on ReadXHub."
    guarded_reply, res = guard.validate_and_guard(hallucinated_reply)

    assert res.is_valid is False
    assert res.correction_applied is True
    assert "Operation Not Completed" in guarded_reply
    assert "browser.save_draft" in guarded_reply
    assert "save confirmation toast did not appear" in guarded_reply


def test_scenario_4_failed_first_attempt_resolved_by_successful_retry():
    """
    Scenario 4:
    A first attempt fails or is unverified, but a subsequent retry or alternate command
    succeeds with verification.
    The guard must recognize that the target is RESOLVED and NOT block the final success claim.
    """
    guard = CompletionGuard()
    guard.start_turn()

    target_path = "/tmp/workspace/script.py"

    # Attempt 1: Fails
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": target_path, "content": "prnt('hi')"},
        status=ToolExecutionStatus.FAILED,
        verified=False,
        reason_or_error="Syntax check failed",
    )

    # Attempt 2: Succeeds and is verified on disk
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": target_path, "content": "print('hi')"},
        status=ToolExecutionStatus.SUCCESS,
        verified=True,
        output_snippet="[FILE_WRITE_VERIFIED] Written 12 bytes",
    )

    resolved, op = guard.is_target_resolved(target_path, "script.py")
    assert resolved is True
    assert op.verified is True

    # Model reports that it created script.py
    model_reply = "I have successfully created script.py with the verified print statement."
    guarded_reply, res = guard.validate_and_guard(model_reply, workspace="/tmp/workspace")

    # Because script.py was successfully resolved in attempt 2, it is NOT an unresolved failure
    assert res.is_valid is True
    assert res.correction_applied is False
    assert guarded_reply == model_reply


def test_scenario_5_partial_completion_reporting():
    """
    Scenario 5:
    One tool operation succeeds with verification, while another tool operation is denied/failed.
    The guard distinguishes between the verified success and the failed operation,
    producing an accurate partial completion report instead of marking everything failed.
    """
    guard = CompletionGuard()
    guard.start_turn()

    # Success 1: config.json
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": "/tmp/workspace/config.json", "content": "{}"},
        status=ToolExecutionStatus.SUCCESS,
        verified=True,
        output_snippet="[FILE_WRITE_VERIFIED] 2 bytes written and verified on disk.",
    )

    # Denied 2: /etc/hosts
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": "/etc/hosts", "content": "127.0.0.1 bad"},
        status=ToolExecutionStatus.DENIED,
        verified=False,
        reason_or_error="Target path '/etc/hosts' is outside the allowed workspace boundary.",
    )

    # Model falsely claims everything succeeded
    hallucinated_reply = "I have created config.json and updated /etc/hosts with your settings."
    guarded_reply, res = guard.validate_and_guard(hallucinated_reply, workspace="/tmp/workspace")

    assert res.is_valid is False
    assert res.correction_applied is True
    assert "Task Partially Completed" in guarded_reply
    assert "Verified Successful Operations:" in guarded_reply
    assert "config.json" in guarded_reply
    assert "Failed / Denied Operations:" in guarded_reply
    assert "/etc/hosts" in guarded_reply
    assert "Only the verified operations above took effect" in guarded_reply


def test_scenario_6_unrelated_informational_answer_not_blocked():
    """
    Scenario 6:
    A tool call was denied/failed, but the model provides an informational explanation
    or concept definition that does NOT falsely claim the failed operation succeeded.
    The guard must NOT block the informational response.
    """
    guard = CompletionGuard()
    guard.start_turn()

    # Tool denied: pinging an external network host
    guard.record_operation(
        tool_name="terminal.run",
        kwargs={"command": "ping 8.8.8.8"},
        status=ToolExecutionStatus.DENIED,
        verified=False,
        reason_or_error="Network commands require explicit full authorization.",
    )

    # Model provides educational answer without falsely claiming it ran ping 8.8.8.8
    info_reply = (
        "An IP address (such as 8.8.8.8) is a unique numerical label assigned to devices "
        "connected to a computer network that uses the Internet Protocol for communication. "
        "Domain Name System (DNS) servers translate human-friendly domain names into these addresses."
    )
    guarded_reply, res = guard.validate_and_guard(info_reply)

    assert res.is_valid is True
    assert res.correction_applied is False
    assert guarded_reply == info_reply


def test_scenario_7_normal_verified_success_clean_passthrough():
    """
    Scenario 7:
    All operations completed with verified success.
    The model's reply passes through cleanly with zero interference or alteration.
    """
    guard = CompletionGuard()
    guard.start_turn()

    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": "/tmp/workspace/main.py", "content": "def main(): pass"},
        status=ToolExecutionStatus.SUCCESS,
        verified=True,
        output_snippet="[FILE_WRITE_VERIFIED] 18 bytes written",
    )

    model_reply = "I have created main.py with the entrypoint function."
    guarded_reply, res = guard.validate_and_guard(model_reply, workspace="/tmp/workspace")

    assert res.is_valid is True
    assert res.correction_applied is False
    assert guarded_reply == model_reply


def test_unified_executor_wires_completion_guard_authoritatively():
    """
    Verifies that UnifiedToolExecutor automatically records operations into completion_guard
    for schema validation errors, permission denials, and execution results.
    """
    registry = ToolRegistry()
    registry.register(DynamicToolDefinition(
        metadata=ToolMetadata(id="test_tool", name="test_tool", category="custom", summary="A test tool", risk_level="low"),
        parameters={"type": "object", "properties": {"param1": {"type": "string"}}, "required": ["param1"]}
    ))

    executor = UnifiedToolExecutor(registry)
    guard = executor.completion_guard
    assert guard is not None

    guard.start_turn()

    # 1. Schema failure
    res_err = executor.execute("test_tool", kwargs={})
    assert res_err.success is False
    unresolved = guard.get_unresolved_failures()
    assert len(unresolved) == 1
    assert unresolved[0].tool_name == "test_tool"
    assert unresolved[0].status == ToolExecutionStatus.FAILED

    # 2. Permission failure
    registry.register(DynamicToolDefinition(
        metadata=ToolMetadata(id="high_tool", name="high_tool", category="custom", summary="High perm tool", risk_level="high"),
        parameters={"type": "object", "properties": {}}
    ))
    res_perm = executor.execute("high_tool", kwargs={}, permission_level="low")
    assert res_perm.success is False
    assert res_perm.was_denied is True
    assert any(op.tool_name == "high_tool" and op.status == ToolExecutionStatus.DENIED for op in guard.operations)


def test_orchestration_pipeline_completion_guard_turn_lifecycle():
    """
    Verifies that OrchestrationPipeline shares the completion_guard with UnifiedToolExecutor
    and cleans turn-scoped operations on start_turn / prepare_request.
    """
    pipeline = OrchestrationPipeline()
    assert pipeline.completion_guard is not None
    assert pipeline.completion_guard is pipeline.executor.completion_guard

    # Record a dummy operation
    pipeline.completion_guard.record_operation(
        tool_name="terminal.run",
        kwargs={"command": "ls"},
        status=ToolExecutionStatus.SUCCESS,
        verified=True
    )
    assert len(pipeline.completion_guard.operations) == 1

    # Start a new turn
    pipeline.completion_guard.start_turn()
    assert len(pipeline.completion_guard.operations) == 0


def test_record_operation_signature_compatibility_and_aliases():
    """
    Verifies that record_operation accepts canonical keyword arguments (kwargs=, reason_or_error=)
    as well as backward-compatible aliases (arguments=, error_snippet=) without raising TypeError.
    """
    guard = CompletionGuard()
    guard.start_turn()

    # 1. Canonical call
    rec1 = guard.record_operation(
        tool_name="terminal.run",
        kwargs={"command": "echo test"},
        status=ToolExecutionStatus.SUCCESS,
        verified=True,
        reason_or_error="",
        output_snippet="test\n"
    )
    assert rec1.target == "echo test"
    assert rec1.status == ToolExecutionStatus.SUCCESS
    assert rec1.verified is True

    # 2. Alias call (arguments=, error_snippet=)
    rec2 = guard.record_operation(
        tool_name="terminal.run",
        arguments={"command": "cat /etc/shadow"},
        status=ToolExecutionStatus.DENIED,
        verified=False,
        error_snippet="Denied by policy",
        output_snippet=""
    )
    assert rec2.target == "cat /etc/shadow"
    assert rec2.status == ToolExecutionStatus.DENIED
    assert rec2.verified is False
    assert rec2.reason_or_error == "Denied by policy"


def test_main_runtime_callpath_recording_success_denial_and_failure():
    """
    Simulates the actual call patterns from lmms/backend/main.py for:
    1. terminal.run successful execution (status=SUCCESS, verified=True)
    2. terminal.run non-zero exit failure (status=FAILED, verified=False)
    3. interactive / security policy denial (status=DENIED, verified=False)
    4. browser.open_authenticated user denial / failure
    Verifies all outcomes are authoritatively stored and guard prevents false claims.
    """
    pipeline = OrchestrationPipeline()
    guard = pipeline.completion_guard
    assert guard is not None
    guard.start_turn()

    # Case A: Successful command
    guard.record_operation(
        tool_name="terminal.run",
        kwargs={"command": "mkdir -p /tmp/testdir"},
        status=ToolExecutionStatus.SUCCESS,
        verified=True,
        reason_or_error="",
        output_snippet=""
    )

    # Case B: Execution error (non-zero exit code)
    guard.record_operation(
        tool_name="terminal.run",
        kwargs={"command": "python -m nonexistent_module"},
        status=ToolExecutionStatus.FAILED,
        verified=False,
        reason_or_error="No module named nonexistent_module",
        output_snippet="Traceback..."
    )

    # Case C: Interactive / security policy denial (from main.py deny branch)
    guard.record_operation(
        tool_name="files.write",
        kwargs={"path": "/etc/sudoers", "content": "ALL ALL=(ALL) NOPASSWD: ALL"},
        status=ToolExecutionStatus.DENIED,
        verified=False,
        reason_or_error="Target path '/etc/sudoers' is outside the allowed workspace boundary ('/tmp').",
        output_snippet=""
    )

    # Case D: Browser open authenticated denied
    guard.record_operation(
        tool_name="browser.open_authenticated",
        kwargs={"url": "https://example.com"},
        status=ToolExecutionStatus.DENIED,
        verified=False,
        reason_or_error="User denied access to browser profile.",
        output_snippet=""
    )

    unresolved = guard.get_unresolved_failures()
    assert len(unresolved) == 3
    unresolved_tools = {op.tool_name for op in unresolved}
    assert unresolved_tools == {"terminal.run", "files.write", "browser.open_authenticated"}

    verified = guard.get_verified_successes()
    assert len(verified) == 1
    assert verified[0].target == "mkdir -p /tmp/testdir"

    # Attempting to claim the denied sudoers file was created
    claim = "I have created /etc/sudoers with the requested settings."
    guarded_text, res = guard.validate_and_guard(claim, workspace="/tmp")
    assert res.is_valid is False
    assert res.correction_applied is True
    assert "Task Partially Completed" in guarded_text
    assert "mkdir -p /tmp/testdir" in guarded_text
    assert "/etc/sudoers" in guarded_text

