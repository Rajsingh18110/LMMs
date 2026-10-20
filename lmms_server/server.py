"""
lmms_server.server - Asyncio JSON-RPC 2.0 IDE App-Server.
Supports Unix domain socket (default, 0600), stdio mode, and optional authenticated localhost TCP.
"""

import argparse
import asyncio
import json
import os
import secrets
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set

from lmms_server.dispatcher import MethodDispatcher
from lmms_server.protocol import (
    BACKPRESSURE_OVERFLOW,
    INTERNAL_ERROR,
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
    """Manages an individual client connection's state, backpressure, and subscriptions."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.outbound_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        self.writer_task: Optional[asyncio.Task[None]] = None
        self.active_tasks: Set[asyncio.Task[Any]] = set()

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
            # Backpressure handling: drop oldest notification or close
            try:
                _ = self.outbound_queue.get_nowait()
                self.outbound_queue.put_nowait(msg)
            except Exception:
                pass

    async def close(self) -> None:
        """Closes reader, writer, and cancels pending connection tasks."""
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
    ):
        self.socket_path = socket_path or get_default_socket_path()
        self.stdio_mode = stdio_mode
        self.tcp_port = tcp_port
        self.auth_token = auth_token
        self.dispatcher = dispatcher or MethodDispatcher()
        self.clients: Set[ClientConnection] = set()
        self.server: Optional[asyncio.Server] = None
        self._is_running = False

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Processes incoming requests from a connected client."""
        client = ClientConnection(reader, writer)
        client.writer_task = asyncio.create_task(client.start_writer())
        self.clients.add(client)

        try:
            while self._is_running:
                line_bytes = await reader.readline()
                if not line_bytes:
                    break  # Client disconnected

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # Process request in task
                req_task = asyncio.create_task(self._process_message(line, client))
                client.active_tasks.add(req_task)
                req_task.add_done_callback(lambda t: client.active_tasks.discard(t))

        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            self.clients.discard(client)
            await client.close()

    async def _process_message(self, raw_line: str, client: ClientConnection) -> None:
        """Parses and executes a single JSON-RPC message."""
        req_id = None
        is_notification = False
        try:
            # Try to grab req_id early if possible, in case parse_request raises later
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

            # Authentication check for TCP mode
            if self.tcp_port and self.auth_token:
                params = req.params if isinstance(req.params, dict) else {}
                provided_token = params.get("auth_token")
                if provided_token != self.auth_token:
                    raise JsonRpcError(UNAUTHORIZED, "Unauthorized: invalid or missing auth_token")

            # Notification emitter closure
            async def emit_notification(method: str, params: Any) -> None:
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

    async def run_stdio(self) -> None:
        """Runs the server over standard input and standard output."""
        self._is_running = True
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)

        await self.handle_client(reader, writer)

    async def start(self) -> None:
        """Starts the server on Unix socket or TCP."""
        self._is_running = True

        if self.stdio_mode:
            await self.run_stdio()
            return

        if self.tcp_port:
            self.server = await asyncio.start_server(
                self.handle_client,
                host="127.0.0.1",
                port=self.tcp_port,
            )
            token_display = self.auth_token or "[none]"
            sys.stderr.write(
                f"[lmms-app-server] Listening on TCP 127.0.0.1:{self.tcp_port} (Auth Token: {token_display})\n"
            )
        else:
            # Unix Domain Socket Mode (Default)
            # Remove stale socket file if it exists
            if os.path.exists(self.socket_path):
                try:
                    os.unlink(self.socket_path)
                except OSError:
                    pass

            # Pre-create parent directory with 0700 permissions
            sock_dir = os.path.dirname(os.path.abspath(self.socket_path))
            os.makedirs(sock_dir, exist_ok=True)
            try:
                os.chmod(sock_dir, 0o700)
            except OSError:
                pass

            self.server = await asyncio.start_unix_server(
                self.handle_client,
                path=self.socket_path,
            )

            # Strictly enforce 0600 permissions on the created socket file
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
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        for client in list(self.clients):
            await client.close()
        self.clients.clear()

        # Remove socket file
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
        sys.stderr.write(f"[lmms-app-server] Generated random TCP auth-token: {auth_token}\n")

    server = AppServer(
        socket_path=args.socket,
        stdio_mode=args.stdio,
        tcp_port=args.tcp,
        auth_token=auth_token,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _sig_handler():
        sys.stderr.write("\n[lmms-app-server] Shutdown signal received, terminating...\n")
        loop.create_task(server.stop())
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _sig_handler)
        except (NotImplementedError, RuntimeError):
            pass

    try:
        loop.run_until_complete(server.start())
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(server.stop())
        loop.close()

    return 0
