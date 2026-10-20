"""
lmms_server.dispatcher - JSON-RPC 2.0 Method Dispatcher.
Integrates session store, MCP tools, worktree isolation, and sandbox policies.
"""

import asyncio
import os
import re
import uuid
from dataclasses import asdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from lmms_mcp.manager import default_mcp_manager
from lmms_sandbox.runner import default_runner
from lmms_server.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    REQUEST_CANCELLED,
    SESSION_NOT_FOUND,
    JsonRpcError,
)
from lmms_sessions.compactor import SessionCompactor
from lmms_sessions.models import Session
from lmms_sessions.store import SessionStore
from lmms_worktree.manager import default_worktree_manager


class MethodDispatcher:
    """Dispatches JSON-RPC 2.0 requests to LMMs subsystem modules."""

    def __init__(
        self,
        store: Optional[SessionStore] = None,
        compactor: Optional[SessionCompactor] = None,
    ):
        self.store = store or SessionStore()
        self.compactor = compactor or SessionCompactor()
        self.pending_permissions: Dict[str, asyncio.Future[bool]] = {}
        self.active_tasks: Dict[str, asyncio.Task[Any]] = {}
        self.default_permission_tier: str = "medium"
        self.stream_generator: Optional[Callable[[str], List[str]]] = None

    async def dispatch(
        self,
        method: str,
        params: Any,
        emit_notification: Callable[[str, Any], Awaitable[None]],
        request_id: Optional[Union[str, int]] = None,
    ) -> Any:
        """Route request by method name."""
        params_dict = params if isinstance(params, dict) else {}

        if method == "initialize":
            return await self.handle_initialize(params_dict)
        elif method == "status":
            return await self.handle_status(params_dict)
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
        elif method == "message.send":
            return await self.handle_message_send(params_dict, emit_notification, request_id)
        elif method == "message.cancel":
            return await self.handle_message_cancel(params_dict)
        elif method == "tool.approve":
            return await self.handle_tool_approve(params_dict)
        elif method == "tool.deny":
            return await self.handle_tool_deny(params_dict)
        elif method == "mcp.list":
            return await self.handle_mcp_list(params_dict)
        elif method == "mcp.call":
            return await self.handle_mcp_call(params_dict)
        elif method == "worktree.status":
            return await self.handle_worktree_status(params_dict)
        elif method == "worktree.diff":
            return await self.handle_worktree_diff(params_dict)
        elif method == "worktree.apply":
            return await self.handle_worktree_apply(params_dict)
        elif method == "worktree.discard":
            return await self.handle_worktree_discard(params_dict)
        elif method == "compact":
            return await self.handle_compact(params_dict)
        else:
            raise JsonRpcError(METHOD_NOT_FOUND, f"Method '{method}' not found")

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns protocol version, server capabilities, and configuration."""
        client_name = params.get("client_name", "unknown")
        client_version = params.get("client_version", "1.0.0")
        return {
            "server_name": "lmms-app-server",
            "server_version": "1.0.0",
            "protocol_version": "2.0",
            "capabilities": {
                "streaming": True,
                "tool_permissions": True,
                "worktree_isolation": True,
                "sqlite_sessions": True,
                "sandbox": True,
                "mcp": True,
            },
            "client_ack": {
                "client_name": client_name,
                "client_version": client_version,
            },
        }

    async def handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Provides overall system health, active sessions count, and sandbox status."""
        sandbox_info = default_runner.get_status()
        sessions = self.store.list_sessions()
        return {
            "status": "ready",
            "active_sessions_count": len(sessions),
            "sandbox": sandbox_info,
            "permission_tier": self.default_permission_tier,
            "mcp_servers_count": len(default_mcp_manager.config.servers),
        }

    async def handle_session_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new session."""
        title = params.get("title", "New Session")
        metadata = params.get("metadata", {})
        session = self.store.create_session(title=title, metadata=metadata)
        return {
            "session_id": session.session_id,
            "title": session.title,
            "parent_session_id": session.parent_session_id,
            "created_at": session.created_at,
        }

    async def handle_session_list(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Lists all existing sessions with counts and metadata."""
        return self.store.list_sessions()

    async def handle_session_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and retrieves full session metadata and messages."""
        session_id = params.get("session_id")
        if not session_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'session_id'")

        session = self.store.get_session(session_id)
        if not session:
            raise JsonRpcError(SESSION_NOT_FOUND, f"Session '{session_id}' not found")

        msgs = self.store.get_messages(session_id)
        return {
            "session_id": session.session_id,
            "title": session.title,
            "parent_session_id": session.parent_session_id,
            "created_at": session.created_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "pinned": m.pinned,
                    "created_at": m.created_at,
                    "metadata": m.metadata,
                }
                for m in msgs
            ],
        }

    async def handle_session_fork(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Forks a session branching from source session."""
        session_id = params.get("session_id")
        if not session_id:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameter 'session_id'")

        title = params.get("title")
        try:
            forked = self.store.fork_session(session_id, new_title=title)
            return {
                "session_id": forked.session_id,
                "title": forked.title,
                "parent_session_id": forked.parent_session_id,
                "created_at": forked.created_at,
            }
        except ValueError as ve:
            raise JsonRpcError(SESSION_NOT_FOUND, str(ve))

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
        as JSON-RPC notifications and checking tool permissions.
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

        # 1. Add user message to session
        self.store.add_message(session_id, role="user", content=content)

        # 2. Check for custom test generator or default generation
        generator = self.stream_generator or params.get("mock_stream_generator")
        tier = params.get("permission_tier") or self.default_permission_tier

        # Generate / stream response
        full_response = ""
        try:
            if generator is not None:
                chunks = generator(content)
            else:
                # Default response generator
                chunks = [f"Echo: {content}"]

            for chunk in chunks:
                # Allow cancellation
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

                # Detect tool calls
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

                            approved = await fut
                            if not approved:
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
        """Lists active MCP servers and registered tools."""
        return default_mcp_manager.list_tools()

    async def handle_mcp_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calls a tool on a registered MCP server."""
        server_name = params.get("server_name")
        tool_name = params.get("tool_name")
        arguments = params.get("arguments", {})
        if not server_name or not tool_name:
            raise JsonRpcError(INVALID_PARAMS, "Missing required parameters 'server_name' and 'tool_name'")

        try:
            res = await default_mcp_manager.call_tool(server_name, tool_name, arguments)
            return {"result": res}
        except Exception as e:
            raise JsonRpcError(INTERNAL_ERROR, f"MCP execution error: {e}")

    async def handle_worktree_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns worktree isolation status for the given repository path."""
        repo_path = params.get("repo_path") or os.getcwd()
        return asdict(default_worktree_manager.status(repo_path))

    async def handle_worktree_diff(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Returns git diff between current branch and isolated worktree."""
        repo_path = params.get("repo_path") or os.getcwd()
        diff_str = default_worktree_manager.diff(repo_path)
        return {"repo_path": repo_path, "diff": diff_str}

    async def handle_worktree_apply(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Applies/merges worktree changes back into the main branch."""
        repo_path = params.get("repo_path") or os.getcwd()
        ok = default_worktree_manager.apply(repo_path)
        return {"repo_path": repo_path, "applied": ok}

    async def handle_worktree_discard(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Discards uncommitted worktree changes and cleans up."""
        repo_path = params.get("repo_path") or os.getcwd()
        ok = default_worktree_manager.discard(repo_path)
        return {"repo_path": repo_path, "discarded": ok}

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
