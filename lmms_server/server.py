"""
lmms_server.server - Asyncio JSON-RPC 2.0 IDE App-Server.
Supports Unix domain socket (default, 0600), stdio mode, and optional authenticated localhost TCP.
Enforces message size limits, strict TCP authentication via hmac.compare_digest,
disconnect cleanup, and live CLI state synchronization.
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import os
import secrets
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set

from lmms_server.dispatcher import MethodDispatcher
from lmms_server.protocol import (
    BACKPRESSURE_OVERFLOW,
    INTERNAL_ERROR,
    PARSE_ERROR,
    REQUEST_CANCELLED,
    UNAUTHORIZED,
    JsonRpcError,
    format_error,
    format_notification,
    format_response,
    parse_request,
)


def get_default_socket_path() -> str:
    """Returns the per-user runtime directory socket path."""
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime and os.path.isdir(xdg_runtime):
        base_dir = Path(xdg_runtime) / "lmms"
    else:
        base_dir = Path.home() / ".lmms"

    base_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(base_dir), 0o700)
    except OSError:
        pass

    return str(base_dir / "lmms.sock")


class ClientConnection:
    """Represents an active client connection with inbound/outbound queues."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.outbound_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        self.writer_task: Optional[asyncio.Task[None]] = None
        self.active_tasks: Set[asyncio.Task[Any]] = set()
        self.pending_prompt_ids: Set[str] = set()

    async def start_writer(self) -> None:
        """Continuously flushes messages from outbound queue to client transport."""
        try:
            while True:
                msg = await self.outbound_queue.get()
                self.writer.write(msg.encode("utf-8"))
                await self.writer.drain()
                self.outbound_queue.task_done()
        except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
            pass

    async def send_raw(self, msg: str) -> None:
        """Pushes serialized message to outbound queue respecting backpressure."""
        try:
            self.outbound_queue.put_nowait(msg)
        except asyncio.QueueFull:
            try:
                _ = self.outbound_queue.get_nowait()
                self.outbound_queue.put_nowait(msg)
            except Exception:
                pass

    async def close(self) -> None:
        """Closes reader, writer, and cancels pending connection tasks."""
        try:
            while not self.outbound_queue.empty():
                m = self.outbound_queue.get_nowait()
                self.writer.write(m.encode("utf-8"))
            await self.writer.drain()
        except Exception:
            pass

        if self.writer_task and not self.writer_task.done():
            self.writer_task.cancel()
        for t in list(self.active_tasks):
            if not t.done():
                t.cancel()
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass


class AppServer:
    """Asyncio JSON-RPC 2.0 Server supporting Unix domain sockets, stdio, and localhost TCP."""

    def __init__(
        self,
        socket_path: Optional[str] = None,
        stdio_mode: bool = False,
        tcp_port: Optional[int] = None,
        auth_token: Optional[str] = None,
        dispatcher: Optional[MethodDispatcher] = None,
        max_message_size: int = 4 * 1024 * 1024,  # 4 MB default
    ):
        self.socket_path = socket_path or get_default_socket_path()
        self.stdio_mode = stdio_mode
        self.tcp_port = tcp_port
        self.auth_token = auth_token
        self.dispatcher = dispatcher or MethodDispatcher()
        self.max_message_size = max_message_size
        self.clients: Set[ClientConnection] = set()
        self.server: Optional[asyncio.Server] = None
        self._is_running = False
        self._watcher_task: Optional[asyncio.Task[None]] = None
        self._last_mcp_mtime: float = 0.0

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Processes incoming requests from a connected client."""
        client = ClientConnection(reader, writer)
        client.writer_task = asyncio.create_task(client.start_writer())
        self.clients.add(client)

        try:
            while self._is_running:
                try:
                    line_bytes = await reader.readuntil(b"\n")
                except asyncio.LimitOverrunError:
                    # Message exceeded max allowed size
                    err_resp = format_error(
                        None,
                        PARSE_ERROR,
                        f"Message exceeds maximum allowed size ({self.max_message_size} bytes)",
                    )
                    await client.send_raw(err_resp)
                    break
                except (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError):
                    break

                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                req_task = asyncio.create_task(self._process_message(line, client))
                client.active_tasks.add(req_task)
                req_task.add_done_callback(lambda t: client.active_tasks.discard(t))

        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            # Clean up pending tool approvals on client disconnect (default to deny)
            for pid in list(client.pending_prompt_ids):
                fut = self.dispatcher.pending_permissions.pop(pid, None)
                if fut and not fut.done():
                    fut.set_result(False)

            self.clients.discard(client)
            await client.close()

    async def _process_message(self, raw_line: str, client: ClientConnection) -> None:
        """Parses and executes a single JSON-RPC message."""
        req_id = None
        is_notification = False
        try:
            try:
                raw_json = json.loads(raw_line)
                if isinstance(raw_json, dict):
                    raw_id = raw_json.get("id")
                    if isinstance(raw_id, (str, int)):
                        req_id = raw_id
            except Exception:
                pass

            req = parse_request(raw_line)
            req_id = req.id
            is_notification = req.is_notification

            # Authentication check for TCP mode (evaluated before any method dispatch)
            if self.tcp_port and self.auth_token:
                params = req.params if isinstance(req.params, dict) else {}
                provided_token = params.get("auth_token")
                if not provided_token or not hmac.compare_digest(str(provided_token), str(self.auth_token)):
                    raise JsonRpcError(UNAUTHORIZED, "Unauthorized: invalid or missing auth_token")

            # Notification emitter closure
            async def emit_notification(method: str, params: Any) -> None:
                if method == "tool.permission_request" and isinstance(params, dict):
                    pid = params.get("prompt_id")
                    if pid:
                        client.pending_prompt_ids.add(str(pid))

                msg = format_notification(method, params)
                await client.send_raw(msg)

            # Register task for message.cancel
            if req_id is not None:
                self.dispatcher.active_tasks[str(req_id)] = asyncio.current_task()  # type: ignore

            result = await self.dispatcher.dispatch(
                method=req.method,
                params=req.params,
                emit_notification=emit_notification,
                request_id=req_id,
            )

            if not req.is_notification and req_id is not None:
                resp = format_response(req_id, result)
                await client.send_raw(resp)

        except JsonRpcError as jerr:
            if not is_notification:
                err_resp = format_error(req_id, jerr.code, jerr.message, jerr.data)
                await client.send_raw(err_resp)
        except asyncio.CancelledError:
            if not is_notification and req_id is not None:
                err_resp = format_error(req_id, REQUEST_CANCELLED, "Request cancelled")
                await client.send_raw(err_resp)
        except Exception as exc:
            if not is_notification and req_id is not None:
                err_resp = format_error(req_id, INTERNAL_ERROR, f"Internal server error: {exc}")
                await client.send_raw(err_resp)
        finally:
            if req_id is not None:
                self.dispatcher.active_tasks.pop(str(req_id), None)

    async def _watch_mcp_config_loop(self) -> None:
        """Watches ~/.lmms/mcp.json for changes made by external CLI commands with debounce and echo suppression."""
        cfg_path = self.dispatcher.mcp_config.config_path
        try:
            if os.path.exists(cfg_path):
                self._last_mcp_mtime = os.path.getmtime(cfg_path)
        except OSError:
            pass

        while self._is_running:
            await asyncio.sleep(0.3)  # 300ms debounce
            try:
                if os.path.exists(cfg_path):
                    mtime = os.path.getmtime(cfg_path)
                    if mtime > self._last_mcp_mtime:
                        self._last_mcp_mtime = mtime
                        # Echo suppression: ignore writes made recently by app-server itself
                        last_internal = getattr(self.dispatcher.mcp_config, "last_internal_write_time", 0.0)
                        if abs(time.time() - last_internal) < 0.6:
                            continue

                        self.dispatcher.mcp_config.load()
                        # Broadcast notification to all connected clients
                        event_msg = format_notification(
                            "mcp.status_changed",
                            {"source": "cli_sync", "status": "reloaded"},
                        )
                        for c in list(self.clients):
                            await c.send_raw(event_msg)
            except Exception:
                pass

    async def run_stdio(self) -> None:
        """Runs the server over standard input and standard output."""
        self._is_running = True
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader(limit=self.max_message_size)
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)

        await self.handle_client(reader, writer)

    async def start(self) -> None:
        """Starts the server on Unix socket or TCP."""
        self._is_running = True
        self._watcher_task = asyncio.create_task(self._watch_mcp_config_loop())

        if self.stdio_mode:
            await self.run_stdio()
            return

        if self.tcp_port:
            self.server = await asyncio.start_server(
                self.handle_client,
                host="127.0.0.1",
                port=self.tcp_port,
                limit=self.max_message_size,
            )
            # Never print or log the auth token
            sys.stderr.write(
                f"[lmms-app-server] Listening on TCP 127.0.0.1:{self.tcp_port} (auth required)\n"
            )
        else:
            # Unix Domain Socket Mode (Default)
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass

            sock_dir = os.path.dirname(os.path.abspath(self.socket_path))
            os.makedirs(sock_dir, exist_ok=True)
            try:
                os.chmod(sock_dir, 0o700)
            except OSError:
                pass

            self.server = await asyncio.start_unix_server(
                self.handle_client,
                path=self.socket_path,
                limit=self.max_message_size,
            )

            try:
                os.chmod(self.socket_path, 0o600)
            except OSError:
                pass

            sys.stderr.write(f"[lmms-app-server] Listening on Unix socket: {self.socket_path} (mode: 0600)\n")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stops the server and cleans up resources."""
        self._is_running = False
        if self._watcher_task and not self._watcher_task.done():
            self._watcher_task.cancel()

        if self.server:
            self.server.close()
            await self.server.wait_closed()

        for client in list(self.clients):
            await client.close()
        self.clients.clear()

        if not self.stdio_mode and not self.tcp_port and self.socket_path:
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass


def run_app_server_cli(argv: list[str]) -> int:
    """CLI entrypoint for `lmms app-server`."""
    parser = argparse.ArgumentParser(description="LMMs IDE App-Server (JSON-RPC 2.0)")
    parser.add_argument("--socket", type=str, default=None, help="Custom Unix socket path")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode for IDE language clients")
    parser.add_argument("--tcp", type=int, default=None, metavar="PORT", help="Enable optional localhost TCP on PORT")
    parser.add_argument("--auth-token", type=str, default=None, help="Auth token required for TCP connections")

    args = parser.parse_args(argv)

    auth_token = args.auth_token
    if args.tcp and not auth_token:
        auth_token = secrets.token_hex(16)
        # CLI convenience output to user directly on startup
        sys.stderr.write(f"[lmms-app-server] Generated one-time TCP auth-token for session: {auth_token}\n")

    server = AppServer(
        socket_path=args.socket,
        stdio_mode=args.stdio,
        tcp_port=args.tcp,
        auth_token=auth_token,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _handle_signal():
        loop.create_task(server.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(server.start())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        loop.run_until_complete(server.stop())
        loop.close()

    return 0
