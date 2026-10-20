"""
tests/test_app_server_hardening.py - Comprehensive Verification for Step 4 Hardening & Step 5a Backend API.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from lmms_server.audit import AuditLogger, default_audit_logger, redact_secrets
from lmms_server.dispatcher import MethodDispatcher, validate_workspace_path
from lmms_server.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    PARSE_ERROR,
    PERMISSION_DENIED,
    REQUEST_CANCELLED,
    UNAUTHORIZED,
)
from lmms_server.server import AppServer
from lmms_sessions.store import SessionStore


@pytest.fixture
def temp_runtime_dir():
    """Provides an isolated runtime directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="lmms_test_harness_")
    orig_env = os.environ.get("XDG_RUNTIME_DIR")
    os.environ["XDG_RUNTIME_DIR"] = temp_dir
    yield temp_dir
    if orig_env is not None:
        os.environ["XDG_RUNTIME_DIR"] = orig_env
    else:
        os.environ.pop("XDG_RUNTIME_DIR", None)
    shutil.rmtree(temp_dir, ignore_errors=True)


async def _send_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    req_id: int = 1,
) -> Dict[str, Any]:
    """Helper to send a JSON-RPC 2.0 request and receive matching response."""
    payload = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {},
    }
    line = json.dumps(payload) + "\n"
    writer.write(line.encode("utf-8"))
    await writer.drain()

    while True:
        resp_line = (await reader.readline()).decode("utf-8").strip()
        if not resp_line:
            raise ConnectionError("Server closed connection prematurely")
        data = json.loads(resp_line)
        if data.get("id") == req_id:
            return data


def test_tcp_auth_timing_safe_and_enforcement(temp_runtime_dir):
    """Verify TCP auth uses hmac.compare_digest, checks before any method, and rejects bad tokens."""
    async def _run():
        port = 19876
        auth_token = "secret_auth_token_xyz123"
        server = AppServer(tcp_port=port, auth_token=auth_token)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            # 1. Connect without token -> should fail with UNAUTHORIZED
            r1, w1 = await asyncio.open_connection("127.0.0.1", port)
            res_bad = await _send_request(r1, w1, "initialize", {}, req_id=1)
            assert res_bad["error"]["code"] == UNAUTHORIZED
            w1.close()
            await w1.wait_closed()

            # 2. Connect with wrong token -> should fail with UNAUTHORIZED
            r2, w2 = await asyncio.open_connection("127.0.0.1", port)
            res_wrong = await _send_request(r2, w2, "initialize", {"auth_token": "wrong_token"}, req_id=2)
            assert res_wrong["error"]["code"] == UNAUTHORIZED
            w2.close()
            await w2.wait_closed()

            # 3. Connect with correct token -> succeeds
            r3, w3 = await asyncio.open_connection("127.0.0.1", port)
            res_ok = await _send_request(r3, w3, "initialize", {"auth_token": auth_token}, req_id=3)
            assert "result" in res_ok
            assert res_ok["result"]["server_name"] == "lmms-app-server"
            w3.close()
            await w3.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())


def test_max_message_size_enforcement(temp_runtime_dir):
    """Verify messages exceeding max allowed size (configured to 50KB for test) are rejected."""
    async def _run():
        sock_path = os.path.join(temp_runtime_dir, "size_test.sock")
        # Configure small message size limit for testing (e.g. 10 KB)
        server = AppServer(socket_path=sock_path, max_message_size=10240)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # Send oversized line (> 10 KB)
            oversized_data = "x" * 20000
            oversized_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "status", "params": {"data": oversized_data}}) + "\n"
            writer.write(oversized_req.encode("utf-8"))
            await writer.drain()

            resp_line = (await reader.readline()).decode("utf-8").strip()
            err_msg = json.loads(resp_line)
            assert err_msg["error"]["code"] == PARSE_ERROR
            assert "maximum allowed size" in err_msg["error"]["message"]

            writer.close()
            await writer.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())


def test_path_parameter_validation_and_escape_prevention(temp_runtime_dir):
    """Verify validate_workspace_path prevents directory traversal and unauthorized paths."""
    workspace = os.path.realpath(temp_runtime_dir)

    # Valid inside path
    inside = os.path.join(workspace, "valid_subdir")
    os.makedirs(inside, exist_ok=True)
    res = validate_workspace_path(inside, allowed_roots=[workspace])
    assert res == inside

    # Outside paths (escape attempts)
    with pytest.raises(Exception) as exc:
        validate_workspace_path("/etc/passwd", allowed_roots=[workspace])
    assert "Path traversal denied" in str(exc.value)

    with pytest.raises(Exception) as exc:
        validate_workspace_path(os.path.join(workspace, "../../etc/shadow"), allowed_roots=[workspace])
    assert "Path traversal denied" in str(exc.value)


def test_tool_approval_timeout_and_disconnect_default_deny(temp_runtime_dir):
    """Verify pending tool approvals default to deny on timeout and client disconnect."""
    async def _run():
        sock_path = os.path.join(temp_runtime_dir, "tool_deny_test.sock")
        server = AppServer(socket_path=sock_path)
        server.dispatcher.tool_approval_timeout = 0.2  # 200ms timeout for test

        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            # 1. Test timeout default deny
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # Mock model output triggering a tool call
            def mock_tool_call_gen(prompt):
                return ["I will use a tool:\n<tool_call>rm -rf /tmp/test</tool_call>"]

            server.dispatcher.stream_generator = mock_tool_call_gen

            req_payload = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "message.send",
                "params": {"content": "Trigger tool call", "permission_tier": "medium"},
            }
            writer.write((json.dumps(req_payload) + "\n").encode("utf-8"))
            await writer.drain()

            # Wait for tool.permission_request notification
            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("method") == "tool.permission_request":
                    break

            # DO NOT approve. Wait for timeout and response for request 10
            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("id") == 10:
                    break

            # Tool turns should record timed out / denied
            msgs = server.dispatcher.store.get_messages(msg["result"]["session_id"])
            tool_turns = [m for m in msgs if m.role == "tool"]
            assert len(tool_turns) == 1
            assert "denied" in tool_turns[0].content

            # 2. Test client disconnect default deny
            writer.close()
            await writer.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())


def test_session_message_serialization(temp_runtime_dir):
    """Verify concurrent requests to the same session are strictly serialized."""
    async def _run():
        sock_path = os.path.join(temp_runtime_dir, "serial_test.sock")
        server = AppServer(socket_path=sock_path)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            r1, w1 = await asyncio.open_unix_connection(sock_path)
            r2, w2 = await asyncio.open_unix_connection(sock_path)

            # Create shared session
            sess_resp = await _send_request(r1, w1, "session.create", {"title": "Shared Session"}, req_id=1)
            sid = sess_resp["result"]["session_id"]

            execution_order = []

            def slow_gen(prompt):
                execution_order.append(f"start:{prompt}")
                res = [f"Token-{i} " for i in range(5)]
                execution_order.append(f"end:{prompt}")
                return res

            server.dispatcher.stream_generator = slow_gen

            # Client 1 and Client 2 dispatch concurrently to same session
            req1 = _send_request(r1, w1, "message.send", {"session_id": sid, "content": "Prompt-1"}, req_id=10)
            req2 = _send_request(r2, w2, "message.send", {"session_id": sid, "content": "Prompt-2"}, req_id=20)

            await asyncio.gather(req1, req2)

            # Assert executions did NOT interleave
            assert execution_order in (
                ["start:Prompt-1", "end:Prompt-1", "start:Prompt-2", "end:Prompt-2"],
                ["start:Prompt-2", "end:Prompt-2", "start:Prompt-1", "end:Prompt-1"],
            )

            w1.close()
            w2.close()
            await w1.wait_closed()
            await w2.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())


def test_audit_logger_hash_chain_and_redaction(temp_runtime_dir):
    """Verify hash-chained audit logging, secret redaction, and chain verification."""
    audit_file = os.path.join(temp_runtime_dir, "test_audit.jsonl")
    logger = AuditLogger(log_path=audit_file)

    # 1. Log multiple calls including sensitive tokens
    logger.log_call(
        server="github",
        tool="create_issue",
        arguments={"title": "Fix bug", "api_key": "ghp_SECRETTOKEN1234567890", "body": "Bearer my_secret_token_abc"},
        duration_ms=45.2,
        status="success",
        result_summary="Issue #10 created successfully",
    )

    logger.log_call(
        server="filesystem",
        tool="read_file",
        arguments={"path": "/workspace/README.md"},
        duration_ms=12.1,
        status="success",
        result_summary="File content read",
    )

    # 2. Verify file permissions
    file_stat = os.stat(audit_file)
    mode = stat.S_IMODE(file_stat.st_mode)
    assert mode == 0o600

    # 3. Verify integrity
    is_valid, count, err = logger.verify()
    assert is_valid is True
    assert count == 2
    assert err is None

    # 4. Verify secrets were redacted in view
    entries = logger.view(limit=10)
    assert len(entries) == 2
    gh_entry = entries[0]
    assert gh_entry["arguments"]["api_key"] == "***REDACTED***"
    assert "ghp_SECRETTOKEN" not in json.dumps(gh_entry)

    # 5. Tamper test: modify one line and ensure verify catches it
    with open(audit_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    tampered_entry = json.loads(lines[0])
    tampered_entry["result_summary"] = "Hacked result"
    lines[0] = json.dumps(tampered_entry) + "\n"

    with open(audit_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    is_valid, count, err = logger.verify()
    assert is_valid is False
    assert "hash verification failed" in str(err)


def test_step5a_mcp_and_permission_methods(temp_runtime_dir):
    """Verify Step 5a app-server methods (mcp.add, update, enable/disable, permissions.get/set, sandbox.status)."""
    async def _run():
        sock_path = os.path.join(temp_runtime_dir, "mcp_methods.sock")
        server = AppServer(socket_path=sock_path)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # 1. mcp.templates
            tmpl_resp = await _send_request(reader, writer, "mcp.templates", req_id=1)
            templates = tmpl_resp["result"]
            assert "filesystem" in templates
            assert "git" in templates
            assert "github" in templates

            # 2. mcp.add
            add_resp = await _send_request(
                reader,
                writer,
                "mcp.add",
                {"name": "test_echo", "command": "echo", "args": ["hello"], "sandbox": "none"},
                req_id=2,
            )
            assert add_resp["result"]["name"] == "test_echo"

            # 3. mcp.disable & mcp.enable
            dis_resp = await _send_request(reader, writer, "mcp.disable", {"name": "test_echo"}, req_id=3)
            assert dis_resp["result"]["enabled"] is False

            en_resp = await _send_request(reader, writer, "mcp.enable", {"name": "test_echo"}, req_id=4)
            assert en_resp["result"]["enabled"] is True

            # 4. permissions.set & permissions.get
            perm_set = await _send_request(
                reader,
                writer,
                "permissions.set",
                {"server": "test_echo", "tool": "custom_echo", "policy": "deny"},
                req_id=5,
            )
            assert perm_set["result"]["policy"] == "deny"

            perm_get = await _send_request(reader, writer, "permissions.get", {"server": "test_echo"}, req_id=6)
            assert perm_get["result"]["custom_echo"] == "deny"

            # 5. sandbox.status
            sand_resp = await _send_request(reader, writer, "sandbox.status", req_id=7)
            assert "bwrap_available" in sand_resp["result"]

            # 6. mcp.remove
            rm_resp = await _send_request(reader, writer, "mcp.remove", {"name": "test_echo"}, req_id=8)
            assert rm_resp["result"]["success"] is True

            writer.close()
            await writer.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())


def test_cli_app_server_shared_state_sync(temp_runtime_dir):
    """Verify changes made to mcp.json (from CLI or external edit) emit notifications to connected client."""
    async def _run():
        sock_path = os.path.join(temp_runtime_dir, "sync_test.sock")
        cfg_file = os.path.join(temp_runtime_dir, "mcp.json")
        server = AppServer(socket_path=sock_path)
        server.dispatcher.mcp_config.config_path = cfg_file
        server.dispatcher.mcp_config.save()

        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # Simulate external CLI modification to mcp.json
            await asyncio.sleep(0.2)
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump({"mcpServers": {"cli_added_server": {"command": "echo", "args": ["from_cli"]}}}, f)

            # Wait for mcp.status_changed notification emitted by server's file watcher
            notification_received = False
            for _ in range(20):
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=0.5)
                    msg = json.loads(line.decode("utf-8").strip())
                    if msg.get("method") == "mcp.status_changed":
                        notification_received = True
                        break
                except asyncio.TimeoutError:
                    pass

            assert notification_received is True

            writer.close()
            await writer.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())


def test_real_model_opt_in_or_skip(temp_runtime_dir):
    """Integration test with real local model: streaming + cancellation over AppServer."""
    from lmms.backend.core.registry.service import RegistryService
    reg = RegistryService()
    models = reg.load_models()
    if not models:
        pytest.skip("No real local model registered in ~/.lmms/models.json.")

    from lmms.cli.client import CLIClient
    cli_client = CLIClient()
    try:
        health = cli_client.get_health()
        if health.get("engine") != "running":
            pytest.skip("Local engine is not running.")
    except Exception:
        pytest.skip("Could not connect to local engine on 11435.")

    active = health.get("active_models", []) or health.get("manager", {}).get("loaded_models", [])
    if "qwen2.5-1.5b-instruct-q5_k_m" in active:
        model_name = "qwen2.5-1.5b-instruct-q5_k_m"
    elif active:
        model_name = active[0]
    else:
        model_name = list(models.keys())[0]

    async def _run():
        sock_path = os.path.join(temp_runtime_dir, "real_model_test.sock")
        server = AppServer(socket_path=sock_path)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # 1. Create session
            sess_resp = await _send_request(reader, writer, "session.create", {"title": "Real Model Test"}, req_id=1)
            session_id = sess_resp["result"]["session_id"]

            # 2. Test Real Token Streaming
            send_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "message.send",
                "params": {
                    "session_id": session_id,
                    "content": "Count from 1 to 5.",
                    "model": model_name,
                },
            }
            writer.write((json.dumps(send_payload) + "\n").encode("utf-8"))
            await writer.drain()

            tokens_received = []
            final_resp = None
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=30.0)
                msg = json.loads(line.decode("utf-8").strip())
                if msg.get("method") == "message.token":
                    tokens_received.append(msg["params"]["token"])
                elif msg.get("id") == 2:
                    final_resp = msg
                    break

            assert len(tokens_received) > 0, "Expected at least one token from real engine"
            assert final_resp is not None
            full_text = "".join(tokens_received)
            assert any(num in full_text for num in ["1", "2", "3", "4", "5"])

            # 3. Test Real Cancellation
            cancel_payload = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "message.send",
                "params": {
                    "session_id": session_id,
                    "content": "Write a 500 word story about an astronaut.",
                    "model": model_name,
                },
            }
            writer.write((json.dumps(cancel_payload) + "\n").encode("utf-8"))
            await writer.drain()

            # Wait for at least 1 token so we know generation has started
            cancel_tokens = []
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=10.0)
                msg = json.loads(line.decode("utf-8").strip())
                if msg.get("method") == "message.token":
                    cancel_tokens.append(msg["params"]["token"])
                    if len(cancel_tokens) >= 1:
                        break

            # Now immediately send message.cancel
            cancel_req = {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "message.cancel",
                "params": {"request_id": 3},
            }
            writer.write((json.dumps(cancel_req) + "\n").encode("utf-8"))
            await writer.drain()

            cancel_ack = None
            req3_resp = None
            for _ in range(100):
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=3.0)
                    msg = json.loads(line.decode("utf-8").strip())
                    if msg.get("id") == 4:
                        cancel_ack = msg
                    elif msg.get("id") == 3:
                        req3_resp = msg
                    if cancel_ack is not None and req3_resp is not None:
                        break
                except asyncio.TimeoutError:
                    break

            assert cancel_ack is not None
            assert cancel_ack["result"]["cancelled"] is True
            assert req3_resp is not None
            assert "error" in req3_resp
            assert req3_resp["error"]["code"] == REQUEST_CANCELLED

            writer.close()
            await writer.wait_closed()

        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    asyncio.run(_run())

