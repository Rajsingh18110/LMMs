"""
Live Event Bus for LMMs OS and Automation Canvas (/panel).
Broadcasts real-time runtime events (tool_start, tool_end, patch_applied,
test_result, error, agent_transition) to local subscribers (UNIX socket / QLocalServer)
and persists them to JSONL for audit and replay.
"""

from __future__ import annotations

import os
import sys
import time
import json
import socket
import select
import threading
from typing import Dict, Any, List, Optional, Callable


class LMMsEventBus:
    """Non-blocking, thread-safe Event Bus for CLI, Agents, and /panel GUI."""

    def __init__(self, socket_path: Optional[str] = None, jsonl_path: Optional[str] = None):
        self.socket_path = socket_path or os.path.expanduser("~/.lmms/events/lmms_events.sock")
        self.jsonl_path = jsonl_path or os.path.expanduser("~/.lmms/events/live_events.jsonl")
        self._lock = threading.Lock()
        self._subscribers: List[socket.socket] = []
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._server_thread: Optional[threading.Thread] = None

        os.makedirs(os.path.dirname(self.socket_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.jsonl_path), exist_ok=True)

        self._start_server()

    def _start_server(self):
        try:
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass

            self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._server_socket.bind(self.socket_path)
            self._server_socket.listen(10)
            self._server_socket.setblocking(False)
            self._running = True

            self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._server_thread.start()
        except Exception:
            # Fallback if UNIX sockets fail (e.g. peculiar FS)
            self._server_socket = None

    def _accept_loop(self):
        while self._running:
            try:
                if not self._server_socket:
                    break
                r, _, _ = select.select([self._server_socket], [], [], 0.5)
                if self._server_socket in r:
                    client, _ = self._server_socket.accept()
                    client.setblocking(False)
                    with self._lock:
                        self._subscribers.append(client)
            except Exception:
                pass

    def subscribe_callback(self, cb: Callable[[Dict[str, Any]], None]):
        """Register an in-process callback (useful for GUI components in the same process)."""
        with self._lock:
            self._callbacks.append(cb)

    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Publish an event across the bus and append to JSONL."""
        payload = {
            "type": event_type,
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            **(data or {}),
            **kwargs,
        }

        # 1. Write to JSONL
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception:
            pass

        # 2. In-process callbacks
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(payload)
            except Exception:
                pass

        # 3. Broadcast to socket subscribers (e.g. /panel GUI subprocess)
        msg_bytes = (json.dumps(payload) + "\n").encode("utf-8")
        dead_clients = []

        with self._lock:
            clients = list(self._subscribers)

        for client in clients:
            try:
                client.sendall(msg_bytes)
            except (BrokenPipeError, ConnectionResetError, OSError):
                dead_clients.append(client)

        if dead_clients:
            with self._lock:
                for dc in dead_clients:
                    if dc in self._subscribers:
                        self._subscribers.remove(dc)
                    try:
                        dc.close()
                    except Exception:
                        pass

        return payload

    # Specific event helpers
    def tool_start(self, tool_name: str, kwargs: Dict[str, Any], step: int = 1) -> Dict[str, Any]:
        return self.emit("tool_start", {"tool": tool_name, "kwargs": kwargs, "step": step})

    def tool_end(self, tool_name: str, success: bool, output: str, duration_ms: float = 0.0) -> Dict[str, Any]:
        return self.emit("tool_end", {
            "tool": tool_name,
            "success": success,
            "output": output[:1000] if isinstance(output, str) else str(output)[:1000],
            "duration_ms": duration_ms
        })

    def patch_applied(self, files_modified: List[str], files_deleted: List[str], diff: str = "") -> Dict[str, Any]:
        return self.emit("patch_applied", {
            "files_modified": files_modified,
            "files_deleted": files_deleted,
            "diff_summary": diff[:500] if diff else ""
        })

    def test_result(self, command: str, exit_code: int, passed: bool, output: str = "") -> Dict[str, Any]:
        return self.emit("test_result", {
            "command": command,
            "exit_code": exit_code,
            "passed": passed,
            "output_preview": output[:500]
        })

    def agent_transition(self, from_agent: str, to_agent: str, reason: str = "") -> Dict[str, Any]:
        return self.emit("agent_transition", {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": reason
        })

    def error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.emit("error", {
            "error_type": error_type,
            "message": message,
            "details": details or {}
        })

    def close(self):
        self._running = False
        with self._lock:
            for c in self._subscribers:
                try:
                    c.close()
                except Exception:
                    pass
            self._subscribers.clear()

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass


# Global singleton
_GLOBAL_BUS: Optional[LMMsEventBus] = None


def get_event_bus() -> LMMsEventBus:
    global _GLOBAL_BUS
    if _GLOBAL_BUS is None:
        _GLOBAL_BUS = LMMsEventBus()
    return _GLOBAL_BUS
