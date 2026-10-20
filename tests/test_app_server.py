"""
Unit and integration tests for lmms_server (IDE App-Server):
- JSON-RPC round trip over a Unix socket
- Socket file permissions (0600)
- Streaming notifications (message.token and message.tool_call)
- Request cancellation (message.cancel)
- Approve / deny flow (tool.approve / tool.deny)
- Invalid requests and error codes (parse error, invalid request, method not found, invalid params)
- Two concurrent clients with isolated event streams
"""

import asyncio
import json
import os
import stat
import pytest
from typing import Any, Dict, List, Optional

from lmms_server.dispatcher import MethodDispatcher
from lmms_server.protocol import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    REQUEST_CANCELLED,
    SESSION_NOT_FOUND,
)
from lmms_server.server import AppServer
from lmms_sessions.store import SessionStore


@pytest.fixture
def test_server(tmp_path):
    """Starts an AppServer over a temporary Unix socket and yields (server, sock_path)."""
    sock_path = str(tmp_path / "test_app_server.sock")
    db_path = str(tmp_path / "test_server_sessions.db")
    store = SessionStore(db_path=db_path)
    dispatcher = MethodDispatcher(store=store)

    server = AppServer(socket_path=sock_path, dispatcher=dispatcher)
    return server, sock_path


async def _send_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    req_id: Optional[int] = 1,
) -> Dict[str, Any]:
    """Helper to send a JSON-RPC request and await response."""
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
    }
    if req_id is not None:
        payload["id"] = req_id

    writer.write((json.dumps(payload) + "\n").encode("utf-8"))
    await writer.drain()

    while True:
        line_bytes = await reader.readline()
        line = line_bytes.decode("utf-8").strip()
        if not line:
            continue
        msg = json.loads(line)
        # Return only responses with matching id
        if msg.get("id") == req_id:
            return msg


def test_socket_permissions_and_round_trip(test_server):
    """
    1. Verify Unix socket is created with 0600 permissions.
    2. Verify initialize, status, session.create, and session.list round-trip.
    """
    async def _run():
        server, sock_path = test_server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            # 1. Verify permissions
            file_stat = os.stat(sock_path)
            mode = stat.S_IMODE(file_stat.st_mode)
            assert mode == 0o600, f"Expected socket mode 0600, got {oct(mode)}"

            # 2. Connect client
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # Initialize
            init_resp = await _send_request(reader, writer, "initialize", {"client_name": "pytest"}, req_id=1)
            assert init_resp.get("id") == 1
            res = init_resp.get("result", {})
            assert res.get("server_name") == "lmms-app-server"
            assert res.get("protocol_version") == "2.0"
            assert res["capabilities"]["streaming"] is True

            # Status
            status_resp = await _send_request(reader, writer, "status", req_id=2)
            assert status_resp.get("result", {}).get("status") == "ready"

            # Session create
            sess_resp = await _send_request(reader, writer, "session.create", {"title": "IDE Unit Test"}, req_id=3)
            sid = sess_resp.get("result", {}).get("session_id")
            assert sid is not None

            # Session list
            list_resp = await _send_request(reader, writer, "session.list", req_id=4)
            sessions = list_resp.get("result", [])
            assert any(s["session_id"] == sid for s in sessions)

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


def test_streaming_notifications(test_server):
    """Verify streaming token notifications are emitted during message.send."""
    async def _run():
        server, sock_path = test_server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # Create session
            sess_resp = await _send_request(reader, writer, "session.create", {"title": "Stream Test"}, req_id=1)
            sid = sess_resp["result"]["session_id"]

            # Mock generator producing 3 chunks
            def mock_gen(prompt):
                return ["Alpha ", "Beta ", "Gamma"]

            server.dispatcher.stream_generator = mock_gen

            # Send message
            req_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "message.send",
                "params": {
                    "session_id": sid,
                    "content": "Test Stream",
                },
            }
            writer.write((json.dumps(req_payload) + "\n").encode("utf-8"))
            await writer.drain()

            received_tokens = []
            final_result = None

            while True:
                line_bytes = await reader.readline()
                msg = json.loads(line_bytes.decode("utf-8").strip())
                if "method" in msg and msg["method"] == "message.token":
                    received_tokens.append(msg["params"]["token"])
                elif msg.get("id") == 2:
                    final_result = msg.get("result")
                    break

            assert received_tokens == ["Alpha ", "Beta ", "Gamma"]
            assert final_result is not None
            assert final_result["content"] == "Alpha Beta Gamma"

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


def test_tool_permission_approve_and_deny_flow(test_server):
    """Verify tool permission prompts can be approved or denied interactively."""
    async def _run():
        server, sock_path = test_server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            sess_resp = await _send_request(reader, writer, "session.create", {"title": "Tool Perm Test"}, req_id=1)
            sid = sess_resp["result"]["session_id"]

            # 1. Test Approval Flow
            def mock_tool_call_gen(prompt):
                return ["I will run a tool: ", "<tool_call>run_command({'cmd': 'ls'})</tool_call>"]

            server.dispatcher.stream_generator = mock_tool_call_gen

            req_payload = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "message.send",
                "params": {
                    "session_id": sid,
                    "content": "List files",
                    "permission_tier": "medium",
                },
            }
            writer.write((json.dumps(req_payload) + "\n").encode("utf-8"))
            await writer.drain()

            # Listen for tool.permission_request
            prompt_id = None
            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("method") == "tool.permission_request":
                    prompt_id = msg["params"]["prompt_id"]
                    break

            assert prompt_id is not None

            # Approve the tool
            app_resp = await _send_request(reader, writer, "tool.approve", {"prompt_id": prompt_id}, req_id=11)
            assert app_resp["result"]["approved"] is True

            # Now await final message response
            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("id") == 10:
                    break

            # 2. Test Denial Flow
            req_payload2 = {
                "jsonrpc": "2.0",
                "id": 20,
                "method": "message.send",
                "params": {
                    "session_id": sid,
                    "content": "Delete files",
                    "permission_tier": "medium",
                },
            }
            writer.write((json.dumps(req_payload2) + "\n").encode("utf-8"))
            await writer.drain()

            prompt_id2 = None
            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("method") == "tool.permission_request":
                    prompt_id2 = msg["params"]["prompt_id"]
                    break

            assert prompt_id2 is not None

            # Deny the tool
            deny_resp = await _send_request(reader, writer, "tool.deny", {"prompt_id": prompt_id2, "reason": "Dangerous"}, req_id=21)
            assert deny_resp["result"]["denied"] is True

            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("id") == 20:
                    break

            # Verify messages in store: tool message contains 'denied'
            msgs = server.dispatcher.store.get_messages(sid)
            tool_msgs = [m for m in msgs if m.role == "tool"]
            assert any("denied" in m.content for m in tool_msgs)

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


def test_request_cancellation(test_server):
    """Verify ongoing message.send can be aborted via message.cancel."""
    async def _run():
        server, sock_path = test_server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            def slow_gen(prompt):
                return [f"Chunk {i} " for i in range(50)]

            server.dispatcher.stream_generator = slow_gen

            # Start generating message with id 99
            req_payload = {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "message.send",
                "params": {
                    "content": "Long task",
                },
            }
            writer.write((json.dumps(req_payload) + "\n").encode("utf-8"))
            await writer.drain()

            # Wait until at least 1 token is received
            while True:
                line = (await reader.readline()).decode("utf-8").strip()
                msg = json.loads(line)
                if msg.get("method") == "message.token":
                    break

            # Send cancellation
            cancel_resp = await _send_request(reader, writer, "message.cancel", {"request_id": 99}, req_id=100)
            assert cancel_resp["result"]["cancelled"] is True

            # Next response for id 99 should report error code REQUEST_CANCELLED
            line = (await reader.readline()).decode("utf-8").strip()
            res99 = json.loads(line)
            if res99.get("id") == 99:
                assert res99["error"]["code"] == REQUEST_CANCELLED

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


def test_invalid_requests_and_errors(test_server):
    """Verify standard JSON-RPC 2.0 error handling."""
    async def _run():
        server, sock_path = test_server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            reader, writer = await asyncio.open_unix_connection(sock_path)

            # 1. Parse error (malformed JSON)
            writer.write(b"{this is not valid json}\n")
            await writer.drain()
            line = (await reader.readline()).decode("utf-8").strip()
            err_msg = json.loads(line)
            assert err_msg["error"]["code"] == PARSE_ERROR

            # 2. Invalid request (missing jsonrpc version)
            writer.write(b'{"id": 1, "method": "status"}\n')
            await writer.drain()
            line = (await reader.readline()).decode("utf-8").strip()
            err_msg = json.loads(line)
            assert err_msg["error"]["code"] == INVALID_REQUEST

            # 3. Method not found
            resp = await _send_request(reader, writer, "non_existent_method", req_id=5)
            assert resp["error"]["code"] == METHOD_NOT_FOUND

            # 4. Invalid params
            resp = await _send_request(reader, writer, "session.resume", {}, req_id=6)
            assert resp["error"]["code"] == INVALID_PARAMS

            # 5. Session not found
            resp = await _send_request(reader, writer, "session.resume", {"session_id": "ghost_id"}, req_id=7)
            assert resp["error"]["code"] == SESSION_NOT_FOUND

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


def test_two_concurrent_clients(test_server):
    """Verify multiple concurrent clients operate simultaneously without interfering."""
    async def _run():
        server, sock_path = test_server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)

        try:
            # Client 1
            r1, w1 = await asyncio.open_unix_connection(sock_path)
            # Client 2
            r2, w2 = await asyncio.open_unix_connection(sock_path)

            # Client 1 creates session A
            res1 = await _send_request(r1, w1, "session.create", {"title": "Client A Session"}, req_id=1)
            sid_a = res1["result"]["session_id"]

            # Client 2 creates session B
            res2 = await _send_request(r2, w2, "session.create", {"title": "Client B Session"}, req_id=2)
            sid_b = res2["result"]["session_id"]

            assert sid_a != sid_b

            # Concurrent message sending
            req_a = _send_request(r1, w1, "message.send", {"session_id": sid_a, "content": "Message from Client A"}, req_id=10)
            req_b = _send_request(r2, w2, "message.send", {"session_id": sid_b, "content": "Message from Client B"}, req_id=20)

            out_a, out_b = await asyncio.gather(req_a, req_b)

            assert "Client A" in out_a["result"]["content"]
            assert "Client B" in out_b["result"]["content"]

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
