#!/usr/bin/env python3
"""
examples/app_server_client.py - Minimal Reference Client for LMMs App-Server.
Connects via Unix Domain Socket or TCP, sends JSON-RPC 2.0 requests,
and receives real-time streaming notifications.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional


class AppServerClient:
    """Async client communicating with lmms app-server over JSON-RPC 2.0."""

    def __init__(self, socket_path: Optional[str] = None, tcp_host: Optional[str] = None, tcp_port: Optional[int] = None, auth_token: Optional[str] = None):
        self.socket_path = socket_path or os.path.expanduser("~/.lmms/lmms.sock")
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.auth_token = auth_token
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._next_id = 1
        self._pending_responses: Dict[int, asyncio.Future[Any]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task[None]] = None

    async def connect(self) -> None:
        """Establishes connection to the app-server."""
        if self.tcp_port:
            host = self.tcp_host or "127.0.0.1"
            self.reader, self.writer = await asyncio.open_connection(host, self.tcp_port)
            print(f"Connected to LMMs App-Server at TCP {host}:{self.tcp_port}")
        else:
            self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
            print(f"Connected to LMMs App-Server at Unix socket: {self.socket_path}")

        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self) -> None:
        """Reads incoming lines from server and routes responses / notifications."""
        assert self.reader is not None
        try:
            while self._running:
                line_bytes = await self.reader.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8").strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except Exception:
                    continue

                # Route response or notification
                if "id" in msg and msg["id"] is not None:
                    req_id = msg["id"]
                    fut = self._pending_responses.pop(req_id, None)
                    if fut and not fut.done():
                        if "error" in msg:
                            fut.set_exception(RuntimeError(msg["error"].get("message", "Unknown error")))
                        else:
                            fut.set_result(msg.get("result"))
                else:
                    # Notification event
                    await self._on_notification(msg.get("method", ""), msg.get("params", {}))

        except (asyncio.CancelledError, ConnectionResetError):
            pass

    async def _on_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Handles streaming notifications."""
        if method == "message.token":
            sys.stdout.write(params.get("token", ""))
            sys.stdout.flush()
        elif method == "message.tool_call":
            tool_name = params.get("tool_name")
            print(f"\n[Model invoked tool: {tool_name}]")
        elif method == "tool.permission_request":
            prompt_id = params.get("prompt_id")
            tool_name = params.get("tool_name")
            print(f"\n[Permission Request: Approve tool '{tool_name}'? (Prompt ID: {prompt_id})]")
            # Auto-approve in this demo
            await self.call("tool.approve", {"prompt_id": prompt_id})
        elif method == "session.compacted":
            print(f"\n[Context Compacted: {params.get('tokens_before')} -> {params.get('tokens_after')} tokens]")

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Sends a JSON-RPC request and awaits result."""
        assert self.writer is not None
        req_id = self._next_id
        self._next_id += 1

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        if self.auth_token:
            payload["params"]["auth_token"] = self.auth_token

        fut: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending_responses[req_id] = fut

        line = json.dumps(payload) + "\n"
        self.writer.write(line.encode("utf-8"))
        await self.writer.drain()

        return await fut

    async def close(self) -> None:
        """Closes connection cleanly."""
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()


async def main():
    client = AppServerClient()
    try:
        await client.connect()

        # 1. Initialize
        init_res = await client.call("initialize", {"client_name": "example-client"})
        print("Initialize Result:", json.dumps(init_res, indent=2))

        # 2. Check Status
        status_res = await client.call("status")
        print("\nStatus Result:", json.dumps(status_res, indent=2))

        # 3. Create Session
        sess = await client.call("session.create", {"title": "Example Client Session"})
        sid = sess["session_id"]
        print(f"\nCreated session: {sid}")

        # 4. Send Message (streams tokens via message.token notifications)
        print("\nSending Message: 'Hello LMMs App Server'...")
        sys.stdout.write("Stream Output: ")
        sys.stdout.flush()
        msg_res = await client.call("message.send", {"session_id": sid, "content": "Hello LMMs App Server"})
        print(f"\nCompleted message response: {msg_res.get('content')}")

    except Exception as e:
        print(f"Client error: {e}", file=sys.stderr)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
