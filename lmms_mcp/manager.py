"""
LMMs MCP Server Manager
Controls server lifecycle (lazy startup, auto-restart, health status, and timeouts)
using the official MCP Python SDK (ClientSession, stdio_client, sse_client).
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from lmms_mcp.config import MCPConfig, MCPServerConfig


@dataclass
class ServerState:
    name: str
    status: str = "stopped"  # "stopped" | "starting" | "connected" | "error"
    session: Optional[ClientSession] = None
    exit_stack: Optional[AsyncExitStack] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    last_error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    restarts: int = 0
    task: Optional[asyncio.Task] = None


class MCPServerManager:
    """Manages active MCP client sessions, lifecycle, and tool discovery."""

    def __init__(self, config: Optional[MCPConfig] = None):
        self.config = config or MCPConfig()
        self.states: Dict[str, ServerState] = {}
        self._lock = asyncio.Lock()
        self._closing = False

    def get_server_state(self, name: str) -> Optional[ServerState]:
        return self.states.get(name)

    def log(self, server_name: str, message: str) -> None:
        """Appends a timestamped log to server's log buffer."""
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        if server_name in self.states:
            state = self.states[server_name]
            state.logs.append(entry)
            if len(state.logs) > 200:
                state.logs.pop(0)

    async def start_server(self, name: str, timeout: float = 15.0) -> ServerState:
        """Starts an MCP server lazily using stdio or SSE transport."""
        async with self._lock:
            if name in self.states and self.states[name].status == "connected":
                return self.states[name]

            server_cfg = self.config.get_server(name)
            if not server_cfg:
                raise ValueError(f"MCP server '{name}' is not configured in ~/.lmms/mcp.json")

            if not server_cfg.enabled:
                raise RuntimeError(f"MCP server '{name}' is disabled.")

            state = self.states.setdefault(name, ServerState(name=name))
            state.status = "starting"
            state.last_error = None
            self.log(name, f"Starting server (transport: {server_cfg.transport})...")

            start_t = time.perf_counter()
            exit_stack = AsyncExitStack()

            try:
                if server_cfg.transport == "stdio":
                    if not server_cfg.command:
                        raise ValueError(f"Stdio server '{name}' requires a command.")

                    env = os.environ.copy()
                    env.update(server_cfg.env or {})

                    cmd = server_cfg.command
                    args = list(server_cfg.args or [])

                    if getattr(server_cfg, "sandbox", "none") in ("bwrap", "sandboxed", "restricted", "auto"):
                        from lmms_sandbox.runner import default_runner
                        if default_runner.bwrap.is_available():
                            workspace = os.getcwd()
                            full_target = [cmd] + args
                            sandboxed_argv = default_runner.bwrap.build_command(
                                command=full_target,
                                workspace_dir=workspace,
                                cwd=workspace,
                                allow_network=True,
                            )
                            cmd = sandboxed_argv[0]
                            args = sandboxed_argv[1:]
                            self.log(name, "Running stdio server under bubblewrap sandbox.")

                    server_params = StdioServerParameters(
                        command=cmd,
                        args=args,
                        env=env,
                    )
                    read, write = await asyncio.wait_for(
                        exit_stack.enter_async_context(stdio_client(server_params)),
                        timeout=timeout,
                    )
                elif server_cfg.transport in ("sse", "http"):
                    if not server_cfg.url:
                        raise ValueError(f"SSE server '{name}' requires a url.")
                    read, write = await asyncio.wait_for(
                        exit_stack.enter_async_context(sse_client(server_cfg.url)),
                        timeout=timeout,
                    )
                else:
                    raise ValueError(f"Unsupported transport '{server_cfg.transport}'")

                session = await exit_stack.enter_async_context(ClientSession(read, write))
                await asyncio.wait_for(session.initialize(), timeout=timeout)

                # Fetch available tools
                tools_res = await asyncio.wait_for(session.list_tools(), timeout=timeout)
                raw_tools = []
                for tool in tools_res.tools:
                    raw_tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": getattr(tool, "inputSchema", {}),
                        "server": name,
                    })

                state.session = session
                state.exit_stack = exit_stack
                state.tools = raw_tools
                state.status = "connected"
                state.latency_ms = (time.perf_counter() - start_t) * 1000.0
                self.log(name, f"Connected successfully! Discovered {len(raw_tools)} tools ({state.latency_ms:.1f}ms).")
                return state

            except Exception as e:
                state.status = "error"
                state.last_error = str(e)
                self.log(name, f"Failed to connect: {e}")
                await exit_stack.aclose()
                raise

    async def stop_server(self, name: str) -> None:
        """Stops an active server and cleans up resources."""
        async with self._lock:
            state = self.states.get(name)
            if not state:
                return

            self.log(name, "Stopping server...")
            if state.exit_stack:
                try:
                    await state.exit_stack.aclose()
                except Exception as e:
                    self.log(name, f"Cleanup error: {e}")

            state.session = None
            state.exit_stack = None
            state.status = "stopped"
            state.tools = []
            self.log(name, "Server stopped.")

    async def restart_server(self, name: str) -> ServerState:
        """Restarts an active or errored server."""
        await self.stop_server(name)
        if name in self.states:
            self.states[name].restarts += 1
        return await self.start_server(name)

    async def list_all_tools(self, filter_server: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns tools across all enabled servers, starting them lazily if needed."""
        servers = self.config.list_servers()
        if filter_server:
            servers = [s for s in servers if s.name == filter_server]

        all_tools: List[Dict[str, Any]] = []
        for server in servers:
            if not server.enabled:
                continue
            try:
                state = await self.start_server(server.name)
                all_tools.extend(state.tools)
            except Exception as e:
                # Log but continue with other servers
                self.log(server.name, f"Tool discovery skipped: {e}")

        return all_tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> Any:
        """Calls a tool on a specific MCP server with auto-start and timeout."""
        state = self.states.get(server_name)
        if not state or state.status != "connected" or not state.session:
            state = await self.start_server(server_name)

        assert state.session is not None, f"Session for {server_name} is null"

        self.log(server_name, f"Calling tool '{tool_name}' with args {arguments}...")
        start_t = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                state.session.call_tool(tool_name, arguments or {}),
                timeout=timeout,
            )
            elapsed = (time.perf_counter() - start_t) * 1000.0
            self.log(server_name, f"Tool '{tool_name}' completed in {elapsed:.1f}ms")
            return result
        except Exception as e:
            self.log(server_name, f"Tool '{tool_name}' error: {e}")
            raise

    async def test_connection(self, name: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Tests connecting to a server and returns (success, message, tools)."""
        try:
            state = await self.restart_server(name)
            return True, f"Connected ({state.latency_ms:.1f}ms)", state.tools
        except Exception as e:
            return False, str(e), []

    def list_tools(self) -> List[Dict[str, Any]]:
        """Aggregates all discovered tools across connected or known servers."""
        all_tools: List[Dict[str, Any]] = []
        for name, state in self.states.items():
            for t in state.tools:
                item = dict(t)
                item["server"] = name
                all_tools.append(item)
        return all_tools

    async def stop_all(self) -> None:
        """Gracefully terminates all active server sessions."""
        self._closing = True
        server_names = list(self.states.keys())
        for name in server_names:
            await self.stop_server(name)


default_mcp_manager = MCPServerManager()
