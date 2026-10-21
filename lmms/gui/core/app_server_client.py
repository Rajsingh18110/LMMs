"""
lmms.gui.core.app_server_client - Qt-integrated Async JSON-RPC 2.0 client.
Connects the desktop GUI to the LMMs App-Server over Unix domain socket.
Dispatches server notifications as Qt signals.
"""

from __future__ import annotations

import asyncio
import atexit
import fcntl
import json
import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, Optional

from lmms.gui.qt import QObject, pyqtSignal
from lmms_server.server import get_default_socket_path


class GUIAppServerClient(QObject):
    """Qt-compatible JSON-RPC 2.0 Client for App-Server with auto-reconnect and lifecycle management."""

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    reconnecting = pyqtSignal(int, float)
    notification_received = pyqtSignal(str, dict)
    mcp_status_changed = pyqtSignal(dict)
    mcp_tool_call = pyqtSignal(dict)
    mcp_log = pyqtSignal(dict)
    tool_permission_request = pyqtSignal(dict)

    def __init__(self, socket_path: Optional[str] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.socket_path = socket_path or get_default_socket_path()
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._next_id = 1
        self._pending_responses: Dict[int, asyncio.Future[Any]] = {}
        self._is_running = False
        self._listener_task: Optional[asyncio.Task[None]] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self.auto_reconnect_enabled = True
        self.mock_dispatcher: Optional[Any] = None
        self._spawned_process: Optional[subprocess.Popen[Any]] = None

    async def ensure_server_running(self) -> bool:
        """
        Starts app-server background process if not already running.
        Uses an atomic lock file to prevent race conditions when multiple GUI instances start simultaneously.

        Lifecycle Rule:
        If this GUI instance spawns the server process, that process is owned by this instance
        and will be terminated cleanly on GUI exit (via close() / atexit).
        If the server was already running before this GUI instance connected, the GUI leaves
        its lifecycle untouched.
        """
        # 1. Fast check if already running and connectable
        if os.path.exists(self.socket_path):
            if await self.connect():
                return True

        lock_path = f"{self.socket_path}.spawn.lock"
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        except OSError:
            lock_fd = None

        try:
            if lock_fd is not None:
                # Acquire exclusive lock, waiting if another GUI instance is currently spawning
                await asyncio.to_thread(fcntl.flock, lock_fd, fcntl.LOCK_EX)

            # Re-check under lock: another GUI window might have just spawned it
            if os.path.exists(self.socket_path):
                if await self.connect():
                    return True

            cmd = [sys.executable, "-m", "lmms_server.server", "--socket", self.socket_path]
            try:
                proc = subprocess.Popen(cmd, start_new_session=True)
                self._spawned_process = proc
                atexit.register(self.shutdown_spawned_server)

                for _ in range(30):
                    await asyncio.sleep(0.1)
                    if os.path.exists(self.socket_path):
                        if await self.connect():
                            return True
            except Exception:
                pass
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    os.close(lock_fd)
                except OSError:
                    pass

        return False

    def shutdown_spawned_server(self) -> None:
        """Terminates server process if it was spawned by this GUI client instance."""
        proc = self._spawned_process
        if proc is not None:
            self._spawned_process = None
            if proc.poll() is None:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=1.0)
                except Exception:
                    pass

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
            if self._reconnect_task and not self._reconnect_task.done():
                self._reconnect_task.cancel()
                self._reconnect_task = None
            self._listener_task = asyncio.create_task(self._listen_loop())
            self.connected.emit()
            return True
        except Exception:
            return False

    async def _reconnect_loop(self) -> None:
        """Exponential backoff reconnect loop (1s, 2s, 4s, 8s, 16s)."""
        delay = 1.0
        attempt = 1
        while self.auto_reconnect_enabled and not self._is_running:
            self.reconnecting.emit(attempt, delay)
            await asyncio.sleep(delay)
            if await self.connect():
                break
            delay = min(delay * 2.0, 16.0)
            attempt += 1
        self._reconnect_task = None

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
                    elif method == "tool.permission_request":
                        self.tool_permission_request.emit(params)

        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self._is_running = False
            self.disconnected.emit()
            if self.auto_reconnect_enabled and (self._reconnect_task is None or self._reconnect_task.done()):
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Sends a JSON-RPC request and awaits result."""
        if self.mock_dispatcher:
            # Synchronous in-memory dispatch for unit tests
            async def _dummy_emit(m: str, p: Any):
                p_dict = p if isinstance(p, dict) else {}
                self.notification_received.emit(m, p_dict)
                if m == "mcp.status_changed":
                    self.mcp_status_changed.emit(p_dict)
                elif m == "mcp.tool_call":
                    self.mcp_tool_call.emit(p_dict)
                elif m == "tool.permission_request":
                    self.tool_permission_request.emit(p_dict)

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
        """Disconnects client cleanly and shuts down spawned server if owned."""
        self._is_running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.shutdown_spawned_server()
        self.disconnected.emit()


default_gui_client = GUIAppServerClient()
