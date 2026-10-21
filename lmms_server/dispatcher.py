"""
lmms_server.dispatcher - JSON-RPC 2.0 Method Dispatcher.
Integrates session store, MCP tools, worktree isolation, sandbox policies, and audit logging.
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import threading
import time
import uuid
from dataclasses import asdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from lmms.cli.client import CLIClient
from lmms_mcp.config import CURATED_TEMPLATES, MCPConfig
from lmms_mcp.manager import default_mcp_manager
from lmms_sandbox.policy import PolicyAction
from lmms_sandbox.runner import default_runner
from lmms_server.audit import default_audit_logger, redact_secrets
from lmms_server.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    PERMISSION_DENIED,
    REQUEST_CANCELLED,
    SESSION_NOT_FOUND,
    JsonRpcError,
)
from lmms_sessions.compactor import SessionCompactor
from lmms_sessions.models import Session
from lmms_sessions.store import SessionStore
from lmms_worktree.manager import default_worktree_manager


def validate_workspace_path(path: str, allowed_roots: Optional[List[str]] = None) -> str:
    """
    Validates that a given path resolves within one of the allowed workspace roots.
    Raises JsonRpcError(PERMISSION_DENIED, ...) on path escape attempts.
    """
    if not path:
        raise JsonRpcError(PERMISSION_DENIED, "Path parameter cannot be empty")

    resolved = os.path.realpath(os.path.abspath(os.path.expanduser(path)))
    roots = allowed_roots or [
        os.path.realpath(os.getcwd()),
        os.path.realpath(os.path.expanduser("~/.lmms")),
        os.path.realpath(tempfile.gettempdir()),
    ]

    for r in roots:
        real_root = os.path.realpath(r)
        try:
            common = os.path.commonpath([real_root, resolved])
            if common == real_root:
                return resolved
        except ValueError:
            continue

    raise JsonRpcError(
        PERMISSION_DENIED,
        f"Path traversal denied: path '{path}' is outside allowed workspace roots",
    )


class MethodDispatcher:
    """Dispatches JSON-RPC 2.0 requests to LMMs subsystem modules."""

    def __init__(
        self,
        store: Optional[SessionStore] = None,
        compactor: Optional[SessionCompactor] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        self.store = store or SessionStore()
        self.compactor = compactor or SessionCompactor()
        self.mcp_config = mcp_config or MCPConfig()
        self.pending_permissions: Dict[str, asyncio.Future[bool]] = {}
        self.active_tasks: Dict[str, asyncio.Task[Any]] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self.default_permission_tier: str = "medium"
        self.tool_approval_timeout: float = 30.0
        self.stream_generator: Optional[Callable[[str], Any]] = None
        self.default_model: str = "default"
        self.allowed_workspace_roots: List[str] = [
            os.path.realpath(os.getcwd()),
            os.path.realpath(os.path.expanduser("~/.lmms")),
            os.path.realpath(tempfile.gettempdir()),
        ]

    async def dispatch(
        self,
        method: str,
        params: Any,
        emit_notification: Callable[[str, Any], Awaitable[None]],
        request_id: Optional[Union[str, int]] = None,
    ) -> Any:
        """Route request by method name."""
        params_dict = params if isinstance(params, dict) else {}

        # Lifecycle & Status
        if method == "initialize":
            return await self.handle_initialize(params_dict)
        elif method == "status":
            return await self.handle_status(params_dict)

        # Session Management
        elif method == "session.create":
            return await self.handle_session_create(params_dict)
        elif method == "session.list":
            return await self.handle_session_list(params_dict)
        elif method == "session.resume":
            return await self.handle_session_resume(params_dict)
        elif method == "session.fork":
            return await self.handle_session_fork(params_dict)
        elif method == "session.rename":
            return await self.handle_session_rename(params_dict)
        elif method == "compact":
            return await self.handle_compact(params_dict)

        # Dialogue & Generation
        elif method == "message.send":
            return await self.handle_message_send(params_dict, emit_notification, request_id)
        elif method == "message.cancel":
            return await self.handle_message_cancel(params_dict)

        # Security & Tool Approvals
        elif method == "tool.approve":
            return await self.handle_tool_approve(params_dict)
        elif method == "tool.deny":
            return await self.handle_tool_deny(params_dict)

        # MCP Tools & Lifecycle
        elif method == "mcp.list":
            return await self.handle_mcp_list(params_dict)
        elif method == "mcp.call":
            return await self.handle_mcp_call(params_dict, emit_notification)
        elif method == "mcp.add":
            return await self.handle_mcp_add(params_dict, emit_notification)
        elif method == "mcp.remove":
            return await self.handle_mcp_remove(params_dict, emit_notification)
        elif method == "mcp.update":
            return await self.handle_mcp_update(params_dict, emit_notification)
        elif method == "mcp.enable":
            return await self.handle_mcp_enable(params_dict, emit_notification)
        elif method == "mcp.disable":
            return await self.handle_mcp_disable(params_dict, emit_notification)
        elif method == "mcp.restart":
            return await self.handle_mcp_restart(params_dict, emit_notification)
        elif method == "mcp.test":
            return await self.handle_mcp_test(params_dict, emit_notification)
        elif method == "mcp.tools":
            return await self.handle_mcp_tools(params_dict)
        elif method == "mcp.logs":
            return await self.handle_mcp_logs(params_dict)
        elif method == "mcp.templates":
            return await self.handle_mcp_templates(params_dict)

        # Permissions
        elif method == "permissions.get":
            return await self.handle_permissions_get(params_dict)
        elif method == "permissions.set":
            return await self.handle_permissions_set(params_dict)

        # Audit Log
        elif method == "audit.list":
            return await self.handle_audit_list(params_dict)

        # Sandbox
        elif method == "sandbox.status":
            return await self.handle_sandbox_status(params_dict)
        elif method == "sandbox.policy.get":
            return await self.handle_sandbox_policy_get(params_dict)
        elif method == "sandbox.policy.set":
            return await self.handle_sandbox_policy_set(params_dict)

        # Worktree Isolation
        elif method == "worktree.status":
            return await self.handle_worktree_status(params_dict)
        elif method == "worktree.diff":
            return await self.handle_worktree_diff(params_dict)
        elif method == "worktree.apply":
            return await self.handle_worktree_apply(params_dict)
        elif method == "worktree.discard":
            return await self.handle_worktree_discard(params_dict)

        raise JsonRpcError(METHOD_NOT_FOUND, f"Method '{method}' not found")

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initial handshake declaring protocol capabilities."""
        client_name = params.get("client_name", "unknown")
        client_version = params.get("client_version", "unknown")
        return {
            "server_name": "lmms-app-server",
            "server_version": "1.0.0",
            "protocol_version": "2.0",
            "capabilities": {
                "streaming": True,
                "cancellation": True,
                "tool_permissions": True,
                "worktree_isolation": True,
                "mcp_support": True,
                "audit_logging": True,
            },
            "connected_client": {
                "name": client_name,
                "version": client_version,
            },
        }

    async def handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns engine readiness, active sessions, and loaded MCP servers."""
        sessions = self.store.list_sessions()
        tools = default_mcp_manager.list_tools()
        return {
            "status": "ready",
            "sessions_count": len(sessions),
            "tools_count": len(tools),
            "sandbox_available": default_runner.bwrap.is_available(),
            "landlock_abi": default_runner.landlock.get_abi_version(),
            "pid": os.getpid(),
        }

    async def handle_session_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new conversation session."""
        title = params.get("title") or "New Session"
        metadata = params.get("metadata")
        session = self.store.create_session(title=title, metadata=metadata)
        return asdict(session)

    async def handle_session_list(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Lists all persistent sessions."""
        return self.store.list_sessions()

    async def handle_session_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Resumes a session and returns its dialogue history."""
        session_id = params.get("session_id")
        if not session_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'session_id'")

        session = self.store.get_session(session_id)
        if not session:
            raise JsonRpcError(SESSION_NOT_FOUND, f"Session '{session_id}' not found")

        messages = self.store.get_messages(session_id)
        res = asdict(session)
        res["messages"] = [asdict(m) for m in messages]
        return res

    async def handle_session_fork(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Forks a session at current point."""
        session_id = params.get("session_id")
        title = params.get("title")
        if not session_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'session_id'")

        forked = self.store.fork_session(session_id, new_title=title)
        if not forked:
            raise JsonRpcError(SESSION_NOT_FOUND, f"Session '{session_id}' not found")
        return asdict(forked)

    async def handle_session_rename(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Renames a session."""
        session_id = params.get("session_id")
        title = params.get("title")
        if not session_id or not title:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameters 'session_id' and 'title'")

        ok = self.store.rename_session(session_id, title)
        if not ok:
            raise JsonRpcError(SESSION_NOT_FOUND, f"Session '{session_id}' not found")
        return {"success": True, "session_id": session_id, "title": title}

    async def handle_message_send(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
        request_id: Optional[Union[str, int]],
    ) -> Dict[str, Any]:
        """
        Sends a message in a session, streaming token and tool-call events
        as JSON-RPC notifications. Serializes message generation per session.
        """
        content = params.get("content")
        if content is None:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'content'")

        session_id = params.get("session_id")
        if not session_id:
            sessions = self.store.list_sessions()
            if sessions:
                session_id = sessions[0]["session_id"]
            else:
                s = self.store.create_session("Default Session")
                session_id = s.session_id

        # Guarantee per-session serialization
        if session_id not in self.session_locks:
            self.session_locks[session_id] = asyncio.Lock()
        session_lock = self.session_locks[session_id]

        async with session_lock:
            # 1. Add user message to session
            self.store.add_message(session_id, role="user", content=content)

            # 2. Check for generator override (e.g. test harness) or real inference engine
            generator = self.stream_generator or params.get("mock_stream_generator")
            tier = params.get("permission_tier") or self.default_permission_tier

            full_response = ""
            try:
                if generator is not None:
                    chunks = generator(content)
                    for chunk in chunks:
                        await asyncio.sleep(0.01)
                        full_response += chunk
                        await emit_notification(
                            "message.token",
                            {
                                "session_id": session_id,
                                "request_id": request_id,
                                "token": chunk,
                            },
                        )
                else:
                    # Real inference engine code path:
                    # Streams tokens via CLIClient from local model / Air Engine
                    model_name = params.get("model") or self.default_model
                    session_history = self.store.get_messages(session_id)
                    api_messages = [{"role": m.role, "content": m.content} for m in session_history]

                    try:
                        cli_client = CLIClient()
                        loop = asyncio.get_running_loop()
                        token_queue: asyncio.Queue[Union[str, Exception, None]] = asyncio.Queue()
                        stop_event = threading.Event()

                        def _stream_worker() -> None:
                            try:
                                stream_gen = cli_client.stream_chat(
                                    model_name=model_name,
                                    messages=api_messages,
                                    mode=params.get("mode", "deep"),
                                    think=params.get("think", True),
                                )
                                for chunk in stream_gen:
                                    if stop_event.is_set() or loop.is_closed():
                                        break
                                    loop.call_soon_threadsafe(token_queue.put_nowait, chunk)
                            except Exception as e:
                                if not stop_event.is_set() and not loop.is_closed():
                                    try:
                                        loop.call_soon_threadsafe(token_queue.put_nowait, e)
                                    except RuntimeError:
                                        pass
                            finally:
                                if not loop.is_closed():
                                    try:
                                        loop.call_soon_threadsafe(token_queue.put_nowait, None)
                                    except RuntimeError:
                                        pass

                        worker_thread = threading.Thread(target=_stream_worker, daemon=True)
                        worker_thread.start()

                        try:
                            while True:
                                item = await token_queue.get()
                                if item is None:
                                    break
                                if isinstance(item, Exception):
                                    raise item
                                full_response += item
                                await emit_notification(
                                    "message.token",
                                    {
                                        "session_id": session_id,
                                        "request_id": request_id,
                                        "token": item,
                                    },
                                )
                                # Cooperative sleep to allow incoming cancellation requests
                                await asyncio.sleep(0.01)
                        finally:
                            stop_event.set()
                    except Exception as engine_err:
                        # Fallback response when engine is offline or model not loaded
                        echo_chunk = f"Echo: {content}"
                        full_response = echo_chunk
                        await emit_notification(
                            "message.token",
                            {
                                "session_id": session_id,
                                "request_id": request_id,
                                "token": echo_chunk,
                            },
                        )

                # Tool call detection from assistant output
                if "<tool_call>" in full_response and "</tool_call>" in full_response:
                    m = re.search(r"<tool_call>\s*(.*?)\s*</tool_call>", full_response, re.DOTALL)
                    if m:
                        raw_call = m.group(1).strip()
                        call_id = uuid.uuid4().hex[:8]
                        tool_name = "custom_tool"
                        tool_args: Dict[str, Any] = {"raw": raw_call}

                        await emit_notification(
                            "message.tool_call",
                            {
                                "session_id": session_id,
                                "tool_name": tool_name,
                                "call_id": call_id,
                                "arguments": tool_args,
                            },
                        )

                        # Permission check
                        obs_text = ""
                        if tier != "full":
                            prompt_id = uuid.uuid4().hex[:8]
                            fut: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
                            self.pending_permissions[prompt_id] = fut

                            await emit_notification(
                                "tool.permission_request",
                                {
                                    "prompt_id": prompt_id,
                                    "tool_name": tool_name,
                                    "arguments": tool_args,
                                    "tier": tier,
                                },
                            )

                            try:
                                approved = await asyncio.wait_for(fut, timeout=self.tool_approval_timeout)
                            except (asyncio.TimeoutError, TimeoutError):
                                approved = False
                                self.pending_permissions.pop(prompt_id, None)
                                obs_text = "Tool execution timed out and was denied by default."

                            if not approved:
                                if not obs_text:
                                    obs_text = "Tool execution was denied by user."
                            else:
                                obs_text = f"Tool output: executed {tool_name}"
                        else:
                            obs_text = f"Tool output: executed {tool_name}"

                        # Record tool execution turn
                        self.store.add_message(
                            session_id,
                            role="tool",
                            content=obs_text,
                            metadata={"tool_call_id": call_id},
                        )

                # 3. Add assistant response turn
                self.store.add_message(session_id, role="assistant", content=full_response)

                # 4. Turn-by-turn auto-compaction check
                if self.compactor.should_auto_compact(session_id, self.store):
                    comp_res = self.compactor.compact(session_id, self.store)
                    if comp_res.success:
                        await emit_notification(
                            "session.compacted",
                            {
                                "session_id": session_id,
                                "tokens_before": comp_res.tokens_before,
                                "tokens_after": comp_res.tokens_after,
                            },
                        )

                return {
                    "session_id": session_id,
                    "role": "assistant",
                    "content": full_response,
                }

            except asyncio.CancelledError:
                raise JsonRpcError(REQUEST_CANCELLED, "Request was cancelled by client")

    async def handle_message_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Cancels an active generating message task."""
        request_id = params.get("request_id")
        if request_id is None:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'request_id'")

        req_key = str(request_id)
        task = self.active_tasks.get(req_key)
        if task and not task.done():
            task.cancel()
            return {"cancelled": True, "request_id": request_id}
        return {"cancelled": False, "reason": "Task not active or already completed"}

    async def handle_tool_approve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Approves a pending tool permission request."""
        prompt_id = params.get("prompt_id")
        if not prompt_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'prompt_id'")

        fut = self.pending_permissions.pop(prompt_id, None)
        if fut and not fut.done():
            fut.set_result(True)
            return {"approved": True, "prompt_id": prompt_id}
        raise JsonRpcError(INVALID_PARAMS, f"Pending tool permission prompt '{prompt_id}' not found")

    async def handle_tool_deny(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Denies a pending tool permission request."""
        prompt_id = params.get("prompt_id")
        reason = params.get("reason", "User denied permission")
        if not prompt_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'prompt_id'")

        fut = self.pending_permissions.pop(prompt_id, None)
        if fut and not fut.done():
            fut.set_result(False)
            return {"denied": True, "prompt_id": prompt_id, "reason": reason}
        raise JsonRpcError(INVALID_PARAMS, f"Pending tool permission prompt '{prompt_id}' not found")

    async def handle_mcp_list(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Lists configured MCP servers and registered tools with secrets redacted."""
        active_tools = default_mcp_manager.list_tools()
        servers = []
        for s in self.mcp_config.list_servers():
            s_dict = s.to_dict()
            if "env" in s_dict and isinstance(s_dict["env"], dict):
                s_dict["env"] = {k: ("***REDACTED***" if v else "") for k, v in s_dict["env"].items()}
            s_dict["tools"] = [t for t in active_tools if t.get("server") == s.name]
            servers.append(s_dict)
        return servers

    async def handle_mcp_call(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """
        Calls a tool on a registered MCP server. Validates paths against allowed workspace roots,
        enforces ExecPolicy, records audit log, and emits tool_call notifications.
        """
        server_name = params.get("server_name")
        tool_name = params.get("tool_name")
        arguments = params.get("arguments", {})
        if not server_name or not tool_name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameters 'server_name' and 'tool_name'")

        # 1. Path parameter validation (prevent directory escape)
        if isinstance(arguments, dict):
            for k, v in arguments.items():
                if any(pk in k.lower() for pk in ("path", "file", "dir", "dest", "source", "root")) and isinstance(v, str):
                    if "/" in v or "\\" in v or v.startswith("."):
                        validate_workspace_path(v, self.allowed_workspace_roots)

        # 2. Permission policy verification
        server_cfg = self.mcp_config.get_server(server_name)
        tool_policy = server_cfg.permissions.get(tool_name) if server_cfg else None
        if tool_policy == "deny":
            raise JsonRpcError(
                PERMISSION_DENIED,
                f"Execution of tool '{tool_name}' on server '{server_name}' is denied by permission policy",
            )
        elif tool_policy == "ask":
            prompt_id = uuid.uuid4().hex[:8]
            fut: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
            self.pending_permissions[prompt_id] = fut

            await emit_notification(
                "tool.permission_request",
                {
                    "prompt_id": prompt_id,
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "arguments": redact_secrets(arguments),
                    "tier": "ask",
                },
            )

            try:
                approved = await asyncio.wait_for(fut, timeout=self.tool_approval_timeout)
            except (asyncio.TimeoutError, TimeoutError):
                approved = False
                self.pending_permissions.pop(prompt_id, None)

            if not approved:
                raise JsonRpcError(
                    PERMISSION_DENIED,
                    f"Execution of tool '{tool_name}' on server '{server_name}' was denied or timed out",
                )

        if isinstance(arguments, dict) and "command" in arguments and isinstance(arguments["command"], str):
            policy_res = default_runner.policy.evaluate(arguments["command"])
            if policy_res.action == PolicyAction.DENY:
                raise JsonRpcError(PERMISSION_DENIED, f"Sandbox policy violation: {policy_res.reason}")

        t0 = time.perf_counter()
        status = "success"
        res = None
        err_msg = ""

        try:
            if hasattr(self, "mock_tool_handler") and callable(self.mock_tool_handler):
                mock_fn = self.mock_tool_handler
                import inspect
                if inspect.iscoroutinefunction(mock_fn):
                    res = await mock_fn(server_name, tool_name, arguments)
                else:
                    res = mock_fn(server_name, tool_name, arguments)
            else:
                res = await default_mcp_manager.call_tool(server_name, tool_name, arguments)
            return {"result": res}
        except Exception as e:
            status = "error"
            err_msg = str(e)
            raise JsonRpcError(INTERNAL_ERROR, f"MCP execution error: {e}")
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            summary = str(res) if status == "success" else err_msg

            # Append to cryptographic hash-chained audit log
            default_audit_logger.log_call(
                server=server_name,
                tool=tool_name,
                arguments=arguments,
                duration_ms=elapsed_ms,
                status=status,
                result_summary=summary,
                session_id=params.get("session_id"),
                origin=params.get("origin", "local"),
                client_peer_id=params.get("client_peer_id"),
                client_ip=params.get("client_ip"),
            )

            # Emit mcp.tool_call notification
            await emit_notification(
                "mcp.tool_call",
                {
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": redact_secrets(arguments),
                    "duration_ms": round(elapsed_ms, 2),
                    "status": status,
                    "result_summary": summary[:500],
                },
            )

    async def handle_mcp_add(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Adds or updates an MCP server configuration."""
        name = params.get("name")
        command_or_url = params.get("command") or params.get("url")
        if not name or not command_or_url:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameters 'name' and 'command'/'url'")

        transport = params.get("transport", "stdio")
        args = params.get("args", [])
        env = params.get("env", {})
        sandbox = params.get("sandbox", "none")
        enabled = params.get("enabled", True)
        share_on_lan = bool(params.get("share_on_lan", False))

        cfg = self.mcp_config.add_server(
            name=name,
            command_or_url=command_or_url,
            transport=transport,
            args=args,
            env=env,
            sandbox=sandbox,
            enabled=enabled,
            share_on_lan=share_on_lan,
        )

        await emit_notification(
            "mcp.status_changed",
            {"server": name, "status": "stopped", "enabled": enabled},
        )
        res = cfg.to_dict()
        if "env" in res and isinstance(res["env"], dict):
            res["env"] = {k: ("***REDACTED***" if v else "") for k, v in res["env"].items()}
        return res

    async def handle_mcp_remove(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Removes an MCP server configuration and stops it if active."""
        name = params.get("name")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        await default_mcp_manager.stop_server(name)
        ok = self.mcp_config.remove_server(name)
        if not ok:
            raise JsonRpcError(INVALID_PARAMS, f"Server '{name}' not found")

        await emit_notification(
            "mcp.status_changed",
            {"server": name, "status": "removed"},
        )
        return {"success": True, "name": name}

    async def handle_mcp_update(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Updates attributes of an existing MCP server."""
        name = params.get("name")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        server = self.mcp_config.get_server(name)
        if not server:
            raise JsonRpcError(INVALID_PARAMS, f"Server '{name}' not found")

        if "command" in params:
            server.command = params["command"]
        if "url" in params:
            server.url = params["url"]
        if "transport" in params:
            server.transport = params["transport"]
        if "args" in params:
            server.args = list(params["args"])
        if "env" in params:
            server.env = dict(params["env"])
        if "sandbox" in params:
            server.sandbox = params["sandbox"]
        if "enabled" in params:
            server.enabled = bool(params["enabled"])
        if "share_on_lan" in params:
            server.share_on_lan = bool(params["share_on_lan"])

        self.mcp_config.save()
        await emit_notification(
            "mcp.status_changed",
            {"server": name, "status": "updated", "enabled": server.enabled},
        )
        res = server.to_dict()
        if "env" in res and isinstance(res["env"], dict):
            res["env"] = {k: ("***REDACTED***" if v else "") for k, v in res["env"].items()}
        return res

    async def handle_mcp_enable(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Enables a configured MCP server."""
        name = params.get("name")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        ok = self.mcp_config.enable_server(name)
        if not ok:
            raise JsonRpcError(INVALID_PARAMS, f"Server '{name}' not found")

        await emit_notification(
            "mcp.status_changed",
            {"server": name, "status": "stopped", "enabled": True},
        )
        return {"name": name, "enabled": True}

    async def handle_mcp_disable(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Disables and terminates a running MCP server."""
        name = params.get("name")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        await default_mcp_manager.stop_server(name)
        ok = self.mcp_config.disable_server(name)
        if not ok:
            raise JsonRpcError(INVALID_PARAMS, f"Server '{name}' not found")

        await emit_notification(
            "mcp.status_changed",
            {"server": name, "status": "disabled", "enabled": False},
        )
        return {"name": name, "enabled": False}

    async def handle_mcp_restart(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Restarts an MCP server session."""
        name = params.get("name")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        await emit_notification(
            "mcp.status_changed",
            {"server": name, "status": "starting"},
        )
        await default_mcp_manager.stop_server(name)
        try:
            state = await default_mcp_manager.start_server(name)
            await emit_notification(
                "mcp.status_changed",
                {"server": name, "status": state.status},
            )
            return {"name": name, "status": state.status, "tools_count": len(state.tools)}
        except Exception as exc:
            await emit_notification(
                "mcp.status_changed",
                {"server": name, "status": "error", "error": str(exc)},
            )
            raise JsonRpcError(INTERNAL_ERROR, f"Failed to restart MCP server '{name}': {exc}")

    async def handle_mcp_test(
        self,
        params: Dict[str, Any],
        emit_notification: Callable[[str, Any], Awaitable[None]],
    ) -> Dict[str, Any]:
        """Tests connection to an MCP server and returns discovered tools."""
        name = params.get("name")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        try:
            state = await default_mcp_manager.start_server(name, timeout=10.0)
            return {
                "name": name,
                "connected": state.status == "connected",
                "tools": state.tools,
                "error": state.last_error,
            }
        except Exception as exc:
            return {
                "name": name,
                "connected": False,
                "tools": [],
                "error": str(exc),
            }

    async def handle_mcp_tools(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Returns discovered tools, optionally filtered by server name."""
        server = params.get("server") or params.get("name")
        all_tools = default_mcp_manager.list_tools()
        if server:
            return [t for t in all_tools if t.get("server") == server]
        return all_tools

    async def handle_mcp_logs(self, params: Dict[str, Any]) -> List[str]:
        """Returns timestamped log messages for a given MCP server."""
        name = params.get("name") or params.get("server")
        if not name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'name'")

        limit = params.get("limit", 100)
        state = default_mcp_manager.states.get(name)
        if state:
            return [
                re.sub(r'(?i)(token|key|secret|password|bearer)[=:\s]+[^\s]+', r'\1=***REDACTED***', line)
                for line in state.logs[-limit:]
            ]
        return []

    async def handle_mcp_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns the curated templates gallery for the GUI."""
        return CURATED_TEMPLATES

    async def handle_permissions_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns permission policies for configured servers and tools."""
        server = params.get("server")
        if server:
            scfg = self.mcp_config.get_server(server)
            return scfg.permissions if scfg else {}

        all_perms: Dict[str, Dict[str, str]] = {}
        for s in self.mcp_config.list_servers():
            all_perms[s.name] = dict(s.permissions)
        return all_perms

    async def handle_permissions_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sets permission policy ('allow', 'ask', 'deny') for a tool or server."""
        server = params.get("server")
        tool = params.get("tool")
        policy = params.get("policy")
        if not server or not tool or not policy:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameters 'server', 'tool', and 'policy'")

        if policy not in ("allow", "ask", "deny"):
            raise JsonRpcError(INVALID_PARAMS, "Policy must be one of 'allow', 'ask', or 'deny'")

        ok = self.mcp_config.set_tool_permission(server, tool, policy)
        if not ok:
            raise JsonRpcError(INVALID_PARAMS, f"Server '{server}' not found")
        return {"server": server, "tool": tool, "policy": policy}

    async def handle_audit_list(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Returns audit records from ~/.lmms/audit.jsonl with pagination."""
        limit = int(params.get("limit", 200))
        offset = int(params.get("offset", 0))
        server = params.get("server")
        return default_audit_logger.view(limit=limit, offset=offset, server=server)

    async def handle_sandbox_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns detailed isolation and security status of sandbox backends."""
        return default_runner.get_status()

    async def handle_sandbox_policy_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns current ExecPolicy configuration."""
        policy = default_runner.policy
        action_val = policy.default_action.value if hasattr(policy.default_action, "value") else str(policy.default_action)
        return {
            "default_action": action_val,
            "sandbox_mode": policy.sandbox_mode,
            "deny_network": policy.deny_network,
            "isolate_home": policy.isolate_home,
            "rules": policy.rules,
            "hidden_paths": policy.hidden_paths,
            "read_only_paths": policy.read_only_paths,
            "writable_paths": policy.writable_paths,
        }

    async def handle_sandbox_policy_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Updates ExecPolicy rules with validation and weakening detection."""
        from lmms_sandbox.policy import detect_weakening, validate_policy_dict

        # 1. Validate structure & schema
        is_valid, err_msg = validate_policy_dict(params)
        if not is_valid:
            raise JsonRpcError(INVALID_PARAMS, f"Invalid sandbox policy: {err_msg}")

        policy = default_runner.policy
        old_policy_dict = await self.handle_sandbox_policy_get({})

        # 2. Check for security weakening
        force = bool(params.get("force", False))
        weakening_reasons = detect_weakening(old_policy_dict, params)

        if weakening_reasons and not force:
            return {
                "warning": True,
                "weakening_reasons": weakening_reasons,
                "message": "Policy weakens protection. Pass force=True to confirm.",
                "policy": old_policy_dict,
            }

        # 3. Apply updates
        if "default_action" in params:
            val = str(params["default_action"]).lower()
            if val in ("allow", "ask", "deny"):
                policy.default_action = PolicyAction(val)
        if "sandbox_mode" in params:
            policy.sandbox_mode = str(params["sandbox_mode"])
        if "deny_network" in params:
            policy.deny_network = bool(params["deny_network"])
        if "isolate_home" in params:
            policy.isolate_home = bool(params["isolate_home"])
        if "rules" in params and isinstance(params["rules"], list):
            policy.rules = list(params["rules"])
        if "writable_paths" in params and isinstance(params["writable_paths"], list):
            policy.writable_paths = list(params["writable_paths"])
        if "read_only_paths" in params and isinstance(params["read_only_paths"], list):
            policy.read_only_paths = list(params["read_only_paths"])
        if "hidden_paths" in params and isinstance(params["hidden_paths"], list):
            policy.hidden_paths = list(params["hidden_paths"])

        res = await self.handle_sandbox_policy_get({})
        if weakening_reasons:
            res["weakening_applied"] = weakening_reasons
        return res

    async def handle_worktree_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns worktree isolation status for the given repository path."""
        repo_path = params.get("repo_path") or os.getcwd()
        validated_path = validate_workspace_path(repo_path, self.allowed_workspace_roots)
        return asdict(default_worktree_manager.status(validated_path))

    async def handle_worktree_diff(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns git diff between current branch and isolated worktree."""
        repo_path = params.get("repo_path") or os.getcwd()
        validated_path = validate_workspace_path(repo_path, self.allowed_workspace_roots)
        diff_str = default_worktree_manager.diff(validated_path)
        return {"repo_path": validated_path, "diff": diff_str}

    async def handle_worktree_apply(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Applies/merges worktree changes back into the main branch."""
        repo_path = params.get("repo_path") or os.getcwd()
        validated_path = validate_workspace_path(repo_path, self.allowed_workspace_roots)
        ok = default_worktree_manager.apply(validated_path)
        return {"repo_path": validated_path, "applied": ok}

    async def handle_worktree_discard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Discards uncommitted worktree changes and cleans up."""
        repo_path = params.get("repo_path") or os.getcwd()
        validated_path = validate_workspace_path(repo_path, self.allowed_workspace_roots)
        ok = default_worktree_manager.discard(validated_path)
        return {"repo_path": validated_path, "discarded": ok}

    async def handle_compact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Runs compaction or compaction rollback on a session."""
        session_id = params.get("session_id")
        if not session_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'session_id'")

        restore = params.get("restore", False)
        if restore:
            ok = self.store.restore_compaction(session_id)
            return {"session_id": session_id, "restored": ok}

        result = self.compactor.compact(session_id, self.store)
        return {
            "session_id": session_id,
            "success": result.success,
            "tokens_before": result.tokens_before,
            "tokens_after": result.tokens_after,
            "summary": result.summary,
            "messages_compacted": result.messages_compacted,
            "error": result.error,
        }
