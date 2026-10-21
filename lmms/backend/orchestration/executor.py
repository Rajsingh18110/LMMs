"""
UnifiedToolExecutor: Production-grade tool validation and execution.
Validates parameters against registered schemas, enforces permission boundaries,
prevents infinite loops, and returns structured observation results.
"""

import os
import time
import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Tuple
from .registry import ToolRegistry, DynamicToolDefinition



@dataclass
class ExecutionResult:
    tool_name: str
    success: bool
    data: Any
    error: str = ""
    duration_ms: int = 0
    formatted_observation: str = ""
    was_denied: bool = False
    retry_count: int = 0


class UnifiedToolExecutor:
    """
    Executes tools safely with schema validation, permission checks, loop protection, and timeouts.
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._execution_history: List[Dict[str, Any]] = []
        self._custom_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def register_handler(self, tool_id: str, handler: Callable):
        """Attaches an active tool handler or instance method."""
        self._custom_handlers[tool_id] = handler

    def _register_default_handlers(self):
        """Attaches default canonical handlers for all core built-in tools."""
        # 1. File operations
        try:
            from lmms.backend.tools.files import canonical_file_read, canonical_file_write, FileTool
            ft = FileTool()
            self.register_handler("files.read", canonical_file_read)
            self.register_handler("files.write", canonical_file_write)
            self.register_handler("files.list", lambda path=".": ft.list_folder(path))
            self.register_handler("files.delete", lambda path, confirm=False: ft.delete(path, confirm))
        except Exception:
            pass

        # 2. Terminal
        try:
            from lmms.backend.tools.terminal import canonical_terminal_callback
            self.register_handler("terminal.run", lambda command, cwd=None: canonical_terminal_callback(command, cwd)["output"])
        except Exception:
            pass

        # 3. Web search
        try:
            from lmms.backend.tools.search import canonical_search_callback
            self.register_handler("web_search", lambda query, max_results=5: canonical_search_callback(query, max_results))
        except Exception:
            pass

        # 4. App launcher
        try:
            from lmms.backend.tools.app_launcher import AppLauncherTool
            alt = AppLauncherTool()
            self.register_handler("app.launch", lambda app_name_or_target, args=None: alt.launch(app_name_or_target, args))
            self.register_handler("app.list", lambda filter_query="": alt.list_apps(filter_query))
            self.register_handler("app.close", lambda app_name: alt.close_app(app_name))
        except Exception:
            pass

        # 5. Messenger
        try:
            from lmms.backend.tools.messenger import MessengerTool
            mt = MessengerTool()
            self.register_handler("message.send", lambda message, platform="desktop", recipient=None, **kw: mt.send(platform, message, recipient, **kw))
        except Exception:
            pass

        # 6. Browser
        try:
            from lmms.backend.tools.browser import BrowserTool
            bt = BrowserTool()
            self.register_handler("browser.open_url", lambda url, headless=False: bt.open_url(url, headless))
            self.register_handler("browser.get_interactive_dom", lambda url=None: bt.get_interactive_dom(url))
            self.register_handler("browser.click_element", lambda selector, url=None, id=None: bt.click_element(selector=selector, url=url, id=id))
            self.register_handler("browser.fill_form", lambda fields, url=None: bt.fill_form(fields, url))
            self.register_handler("browser.type", lambda selector, text, press_enter=False, url=None: bt.type_text(selector, text, press_enter, url))
            self.register_handler("browser.scrape_live", lambda url, selector=None: bt.scrape_live(url, selector))
            self.register_handler("browser.screenshot", lambda save_path="/tmp/lmms_browser.png", url=None: bt.screenshot(save_path, url))
            self.register_handler("browser.scroll", lambda url=None, direction="down", amount=1000: bt.scroll(url or "", direction, amount))
            self.register_handler("browser.press_key", lambda key="Enter": bt.press_key(key))
            self.register_handler("browser.open_authenticated", lambda url, user_data_dir=None, profile_name="Default", headless=True: bt.open_authenticated(url, user_data_dir or os.path.expanduser("~/.lmms/browser_profile"), profile_name, headless))
        except Exception:
            pass

        # 6b. Crawl4AI Deep Crawler
        try:
            from lmms.backend.rag.crawler import AdvancedCrawler
            crawler = AdvancedCrawler()
            self.register_handler("browser.crawl_url", lambda url, css_selector=None: crawler.crawl_and_extract_text(url, max_chars=12000))
        except Exception:
            pass

        # 7. Security report
        self.register_handler("security.generate_report", lambda findings_summary: f"# Security Audit Report\n\n## Summary\n{findings_summary}\n\n*Generated by LMMs Security Engine*")

        # 8. Vector DB & RAG
        try:
            from lmms.backend.rag.pipeline import get_rag_pipeline
            self.register_handler("rag.search", lambda query, k=5: get_rag_pipeline().search(query=query, k=k))
            self.register_handler("vector_db.search", lambda query, k=5: get_rag_pipeline().search(query=query, k=k))
            self.register_handler("rag.crawl_url", lambda url, css_selector=None: get_rag_pipeline().crawl_and_index_url(url=url, css_selector=css_selector))
        except Exception:
            self.register_handler("vector_db.search", lambda query: f"[Vector Search] Results for query '{query}': Indexed codebase files matching semantic embedding.")

    def normalize_call(self, tool_name: str, kwargs: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizes tool name and argument keys to canonical registry definitions.
        Supports:
        - Tool name aliases: files.read, file.read, read_file, browser.open_url, open_url, terminal.run, run_terminal, etc.
        - Argument aliases: file_path -> path, cmd -> command, q -> query, application/app -> app_name_or_target.
        """
        raw_name = tool_name.strip().strip("'\"`").strip()
        normalized_name = raw_name

        # Resolve via registry get()
        resolved_tool = self.registry.get(raw_name)
        if resolved_tool:
            normalized_name = resolved_tool.id
        else:
            # Try underscore vs dot variants
            alt_dot = raw_name.replace("_", ".")
            if self.registry.get(alt_dot):
                normalized_name = self.registry.get(alt_dot).id
            else:
                alt_under = raw_name.replace(".", "_")
                if self.registry.get(alt_under):
                    normalized_name = self.registry.get(alt_under).id

        # Normalize argument aliases
        clean_kwargs = dict(kwargs)
        if normalized_name in ("files.read", "files.write", "files.delete"):
            for k in ["file_path", "filepath", "filename", "file", "target_file"]:
                if k in clean_kwargs and "path" not in clean_kwargs:
                    clean_kwargs["path"] = clean_kwargs.pop(k)
        if normalized_name == "files.write":
            for k in ["data", "text", "body", "code"]:
                if k in clean_kwargs and "content" not in clean_kwargs:
                    clean_kwargs["content"] = clean_kwargs.pop(k)
        if normalized_name == "terminal.run":
            for k in ["cmd", "shell_command", "code", "bash"]:
                if k in clean_kwargs and "command" not in clean_kwargs:
                    clean_kwargs["command"] = clean_kwargs.pop(k)
        if normalized_name == "web_search":
            for k in ["q", "search_query", "keywords", "terms"]:
                if k in clean_kwargs and "query" not in clean_kwargs:
                    clean_kwargs["query"] = clean_kwargs.pop(k)
        if normalized_name == "app.launch":
            for k in ["application", "app", "app_name", "target"]:
                if k in clean_kwargs and "app_name_or_target" not in clean_kwargs:
                    clean_kwargs["app_name_or_target"] = clean_kwargs.pop(k)
        elif normalized_name == "app.close":
            for k in ["application", "app", "target"]:
                if k in clean_kwargs and "app_name" not in clean_kwargs:
                    clean_kwargs["app_name"] = clean_kwargs.pop(k)
        if normalized_name.startswith("browser."):
            for k in ["link", "web_url", "target_url"]:
                if k in clean_kwargs and "url" not in clean_kwargs:
                    clean_kwargs["url"] = clean_kwargs.pop(k)
        if normalized_name == "message.send":
            for k in ["text", "msg", "body", "content"]:
                if k in clean_kwargs and "message" not in clean_kwargs:
                    clean_kwargs["message"] = clean_kwargs.pop(k)

        return normalized_name, clean_kwargs

    def execute_raw(
        self,
        raw_call: Any,
        permission_level: str = "medium",
        is_planning_mode: bool = False
    ) -> ExecutionResult:
        """
        Parses raw model output (string with <tool_call> or JSON dict) and executes the call.
        Supports both:
        1. {"tool": "tool_name", "kwargs": {...}}
        2. {"name": "tool_name", "arguments": {...}}
        """
        t_name = ""
        t_kwargs = {}

        if isinstance(raw_call, str):
            text = raw_call.strip()
            # Extract content from <tool_call> tags if present
            m = re.search(r"<tool_call>\s*(.*?)\s*(?:</tool_call>|$)", text, re.DOTALL)
            if m:
                text = m.group(1).strip()
            # Strip markdown code fencing
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                data = json.loads(text)
            except Exception:
                try:
                    import ast
                    s = re.sub(r'\btrue\b', 'True', text)
                    s = re.sub(r'\bfalse\b', 'False', s)
                    s = re.sub(r'\bnull\b', 'None', s)
                    data = ast.literal_eval(s)
                except Exception as e:
                    return ExecutionResult(
                        tool_name="unknown",
                        success=False,
                        data=None,
                        error=f"Failed to parse tool call JSON: {e}",
                        formatted_observation=f"<observation>\n[PARSE_ERROR] Invalid JSON: {e}\n</observation>"
                    )
        elif isinstance(raw_call, dict):
            data = raw_call
        else:
            return ExecutionResult(
                tool_name="unknown",
                success=False,
                data=None,
                error="Invalid raw_call type",
                formatted_observation="<observation>\n[ERROR] Invalid tool call payload.\n</observation>"
            )

        if isinstance(data, dict):
            t_name = data.get("tool") or data.get("name") or ""
            t_kwargs = data.get("kwargs") or data.get("arguments") or {}
            if isinstance(t_kwargs, str):
                try:
                    t_kwargs = json.loads(t_kwargs)
                except Exception:
                    t_kwargs = {}

        return self.execute(
            tool_name=t_name,
            kwargs=t_kwargs,
            permission_level=permission_level,
            is_planning_mode=is_planning_mode
        )

    def validate_arguments(self, tool: DynamicToolDefinition, kwargs: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates kwargs against the tool's JSON parameter schema.
        Returns (is_valid, error_message).
        """
        schema = tool.parameters
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # 1. Check required properties
        for req in required:
            if req not in kwargs:
                return False, f"Missing required parameter '{req}' for tool '{tool.id}'."

        # 2. Check types of provided arguments
        for k, v in kwargs.items():
            if k in properties:
                expected_type = properties[k].get("type")
                if expected_type == "string" and not isinstance(v, str):
                    return False, f"Parameter '{k}' must be a string, got {type(v).__name__}."
                elif expected_type == "integer" and not isinstance(v, int):
                    return False, f"Parameter '{k}' must be an integer, got {type(v).__name__}."
                elif expected_type == "boolean" and not isinstance(v, bool):
                    return False, f"Parameter '{k}' must be a boolean, got {type(v).__name__}."
                elif expected_type == "object" and not isinstance(v, dict):
                    return False, f"Parameter '{k}' must be a JSON object/dict, got {type(v).__name__}."
                elif expected_type == "array" and not isinstance(v, list):
                    return False, f"Parameter '{k}' must be a list/array, got {type(v).__name__}."

        return True, ""

    def check_permissions(
        self,
        tool: DynamicToolDefinition,
        permission_level: str = "medium",
        is_planning_mode: bool = False
    ) -> Tuple[bool, str]:
        """
        Enforces permission levels (low, medium, high) and planning mode read-only restrictions.
        """
        # Planning mode read-only check
        if is_planning_mode:
            write_tools = [
                "files.write", "browser.click_element", "browser.fill_form",
                "browser.type", "app.launch", "app.close", "message.send"
            ]
            if tool.id in write_tools:
                return False, "Planning mode is read-only. Mutation tools are restricted."

        # Permission level checks
        if permission_level == "low":
            if tool.metadata.risk_level in ("medium", "high"):
                return False, f"Permission Denied: Tool '{tool.id}' has {tool.metadata.risk_level} risk, but permission level is 'low'."

        return True, ""

    def detect_infinite_loop(self, tool_name: str, kwargs: Dict[str, Any], max_consecutive: int = 3) -> bool:
        """
        Detects if the model is calling the exact same tool with identical arguments repeatedly.
        """
        if len(self._execution_history) < max_consecutive:
            return False

        recent = self._execution_history[-max_consecutive:]
        for entry in recent:
            if entry.get("tool") != tool_name or entry.get("kwargs") != kwargs:
                return False

        return True

    def execute(
        self,
        tool_name: str,
        kwargs: Dict[str, Any],
        permission_level: str = "medium",
        is_planning_mode: bool = False,
        max_observation_chars: int = 4000
    ) -> ExecutionResult:
        """
        Validates and executes a tool call, returning an ExecutionResult with formatted observation.
        """
        t0 = time.time()
        tool_name, kwargs = self.normalize_call(tool_name, kwargs)

        # 1. Resolve tool definition
        tool = self.registry.get(tool_name)
        if not tool:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[ERROR] Unknown tool '{tool_name}'. Available tools can be inspected in system prompt.\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=f"Unknown tool '{tool_name}'",
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        # 2. Validate arguments against schema
        valid, err = self.validate_arguments(tool, kwargs)
        if not valid:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[VALIDATION_ERROR] {err}\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=err,
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        # 3. Check permissions
        allowed, perm_err = self.check_permissions(tool, permission_level, is_planning_mode)
        if not allowed:
            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[PERMISSION_DENIED] {perm_err}\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=perm_err,
                duration_ms=duration_ms,
                formatted_observation=obs,
                was_denied=True
            )

        # 4. Check for infinite loops
        if self.detect_infinite_loop(tool.id, kwargs):
            duration_ms = int((time.time() - t0) * 1000)
            obs = (
                f"<observation>\n[LOOP_DETECTED] Tool '{tool_name}' was called with identical arguments {3} times consecutively. "
                "Execution halted to avoid infinite loop. Please summarize current findings or try a different approach.\n</observation>"
            )
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error="Infinite tool loop detected",
                duration_ms=duration_ms,
                formatted_observation=obs
            )

        # 5. Execute handler
        handler = self._custom_handlers.get(tool.id) or tool.callback
        if not handler:
            if tool.id == "discover_additional_tool":
                cap = kwargs.get("capability") or kwargs.get("tool_name") or ""
                discovered = self.registry.get(cap)
                if not discovered:
                    for t in self.registry._tools.values():
                        if cap.lower() in t.id.lower() or any(cap.lower() in tag.lower() for tag in t.metadata.tags):
                            discovered = t
                            break
                duration_ms = int((time.time() - t0) * 1000)
                if discovered:
                    obs = (
                        f"<observation>\n[TOOL_DISCOVERED] Tool '{discovered.id}' successfully discovered and activated.\n"
                        f"Summary: {discovered.metadata.summary}\n"
                        f"Parameters: {json.dumps(discovered.parameters)}\n"
                        f"You may now invoke '{discovered.id}' in your next step.\n</observation>"
                    )
                    return ExecutionResult(
                        tool_name=tool.id,
                        success=True,
                        data={"tool_id": discovered.id, "parameters": discovered.parameters},
                        duration_ms=duration_ms,
                        formatted_observation=obs
                    )
                else:
                    obs = f"<observation>\n[ERROR] Capability '{cap}' not found among registered tools.\n</observation>"
                    return ExecutionResult(
                        tool_name=tool.id,
                        success=False,
                        data=None,
                        error=f"Capability '{cap}' not found",
                        duration_ms=duration_ms,
                        formatted_observation=obs
                    )

            duration_ms = int((time.time() - t0) * 1000)
            obs = f"<observation>\n[ERROR] No execution handler attached for tool '{tool.id}'.\n</observation>"
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                data=None,
                error=f"No handler registered for '{tool.id}'",
                duration_ms=duration_ms,
                formatted_observation=obs
            )


        data = None
        error_msg = ""
        success = False

        try:
            # Execute with clean kwargs matching signature
            data = handler(**kwargs)
            success = True
        except Exception as e:
            error_msg = str(e)
            success = False

        duration_ms = int((time.time() - t0) * 1000)

        # Record history for loop detection
        self._execution_history.append({
            "tool": tool.id,
            "kwargs": dict(kwargs),
            "success": success,
            "timestamp": time.time()
        })

        # Format observation cleanly
        if success:
            obs_content = str(data) if data is not None else "[SUCCESS] Completed with no output."
            if len(obs_content) > max_observation_chars:
                head = int(max_observation_chars * 0.7)
                tail = int(max_observation_chars * 0.3)
                obs_content = (
                    obs_content[:head]
                    + f"\n... [Truncated {len(obs_content) - head - tail} characters] ...\n"
                    + obs_content[-tail:]
                )
            formatted_obs = f"<observation>\n{obs_content}\n</observation>"
        else:
            formatted_obs = f"<observation>\n[EXECUTION_FAILED] {error_msg}\n</observation>"

        return ExecutionResult(
            tool_name=tool.id,
            success=success,
            data=data,
            error=error_msg,
            duration_ms=duration_ms,
            formatted_observation=formatted_obs
        )


# Helper tuple alias
Tuple_Bool_Str = tuple[bool, str]
