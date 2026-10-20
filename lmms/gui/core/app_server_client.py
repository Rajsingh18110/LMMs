"""
lmms.gui.core.app_server_client - Qt-integrated Async JSON-RPC 2.0 client.
Connects the desktop GUI to the LMMs App-Server over Unix domain socket.
Dispatches server notifications as Qt signals.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable, Dict, Optional

from lmms.gui.qt import QObject, pyqtSignal
from lmms_server.server import get_default_socket_path


class GUIAppServerClient(QObject):
    """Qt-compatible JSON-RPC 2.0 Client for App-Server."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    notification_received = pyqtSignal(str, dict)
    mcp_status_changed = pyqtSignal(dict)
    mcp_tool_call = pyqtSignal(dict)
    mcp_log = pyqtSignal(dict)

    def __init__(self, socket_path: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.socket_path = socket_path or get_default_socket_path()
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._next_id = 1
        self._pending_responses: Dict[int, asyncio.Future[Any]] = {}
        self._is_running = False
        self._listener_task: Optional[asyncio.Task[None]] = None
        self.mock_dispatcher: Optional[Any] = None

    async def connect(self) -> bool:
        """Establishes connection to the app-server Unix socket."""
        if self.mock_dispatcher:
            self._is_running = True
            self.connected.emit()
            return True

        if not os.path.exists(self.socket_path):
            return False

        try:
            self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
            self._is_running = True
            self._listener_task = asyncio.create_task(self._listen_loop())
            self.connected.emit()
            return True
        except Exception:
            return False

    async def _listen_loop(self) -> None:
        """Reads incoming JSON-RPC lines from the server socket."""
        assert self.reader is not None
        try:
            while self._is_running:
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

                if "id" in msg and msg["id"] is not None:
                    req_id = msg["id"]
                    fut = self._pending_responses.pop(req_id, None)
                    if fut and not fut.done():
                        if "error" in msg:
                            fut.set_exception(RuntimeError(msg["error"].get("message", "Unknown error")))
                        else:
                            fut.set_result(msg.get("result"))
                else:
                    method = msg.get("method", "")
                    params = msg.get("params", {})
                    self.notification_received.emit(method, params)
                    if method == "mcp.status_changed":
                        self.mcp_status_changed.emit(params)
                    elif method == "mcp.tool_call":
                        self.mcp_tool_call.emit(params)
                    elif method == "mcp.log":
                        self.mcp_log.emit(params)

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self._is_running = False
            self.disconnected.emit()

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Sends a JSON-RPC request and awaits result."""
        if self.mock_dispatcher:
            # Synchronous in-memory dispatch for unit tests
            async def _dummy_emit(m: str, p: Any):
                self.notification_received.emit(m, p if isinstance(p, dict) else {})
                if m == "mcp.status_changed" and isinstance(p, dict):
                    self.mcp_status_changed.emit(p)

            return await self.mock_dispatcher.dispatch(
                method=method,
                params=params or {},
                emit_notification=_dummy_emit,
                request_id=self._next_id,
            )

        if not self.writer or not self._is_running:
            raise ConnectionError("Not connected to LMMs App-Server")

        req_id = self._next_id
        self._next_id += 1

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Any] = loop.create_future()
        self._pending_responses[req_id] = fut

        line = json.dumps(payload) + "\n"
        self.writer.write(line.encode("utf-8"))
        await self.writer.drain()

        return await fut

    async def close(self) -> None:
        """Disconnects client cleanly."""
        self._is_running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.disconnected.emit()


default_gui_client = GUIAppServerClient()
