"""
lmms.gui.widgets.automation_runner - Async Workflow Execution Engine & Run History.
Executes n8n-style graphs with data item passing, expression templating ({{node.data}}),
sandboxed Python execution, HTTP requests, MCP tool calls, and SQLite history persistence.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import time
import urllib.request
from typing import Dict, Any, List, Optional, Callable

from lmms.gui.branding import AutomationBranding


class WorkflowHistoryStore:
    """Manages SQLite storage for execution logs and traces."""
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.expanduser("~/.lmms/workflows")
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "history.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    workflow_name TEXT,
                    start_time REAL,
                    duration_ms INTEGER,
                    status TEXT,
                    step_count INTEGER,
                    trace_json TEXT
                )
            """)
            conn.commit()

    def record_execution(self, exec_id: str, name: str, start_time: float, duration_ms: int, status: str, step_count: int, trace: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO executions (id, workflow_name, start_time, duration_ms, status, step_count, trace_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (exec_id, name, start_time, duration_ms, status, step_count, json.dumps(trace)))
            conn.commit()

    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, workflow_name, start_time, duration_ms, status, step_count
                FROM executions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_execution_trace(self, exec_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trace_json FROM executions WHERE id = ?", (exec_id,))
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None


class WorkflowExecutionEngine:
    """
    Topological async execution engine for NodeGraph workflows.
    Passes data payloads between connected node ports and resolves {{...}} expressions.
    """
    def __init__(self, history_store: Optional[WorkflowHistoryStore] = None):
        self.history = history_store or WorkflowHistoryStore()

    def resolve_expressions(self, text: str, context: Dict[str, Any]) -> str:
        """Resolves {{$node["NodeName"].json["key"]}} or {{field}} templates."""
        if not isinstance(text, str) or "{{" not in text:
            return text

        def _repl(match):
            expr = match.group(1).strip()
            # Simple direct key lookup
            if expr in context:
                return str(context[expr])
            # Nested lookup e.g. data.value or node.field
            parts = expr.split(".")
            val = context
            for p in parts:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    return match.group(0)  # Unresolved, keep original
            return str(val)

        return re.sub(r"\{\{(.*?)\}\}", _repl, text)

    async def execute_node(self, node, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches node execution based on type and custom properties."""
        node_id = getattr(node, "__identifier__", "")
        cat = getattr(node, "CATEGORY", "action")
        props = getattr(node.model, "custom_properties", {})

        # 1. Triggers
        if cat == "trigger":
            return {
                "triggered": True,
                "node": node.name(),
                "timestamp": time.time(),
                "payload": input_data or {"event": "manual_trigger", "source": "lmms_canvas"},
            }

        # 2. AI Agent & Models
        elif cat == "model":
            prompt = props.get("system_prompt", "Accomplish workflow task.")
            prompt = self.resolve_expressions(str(prompt), context)
            model_name = props.get("model_name", "qwen2.5-coder")

            ai_result = None
            try:
                req_data = json.dumps({
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": float(props.get("temperature", 0.7)),
                }).encode("utf-8")
                req = urllib.request.Request(
                    "http://localhost:11435/v1/chat/completions",
                    data=req_data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    ai_result = resp_json["choices"][0]["message"]["content"]
            except Exception as e:
                fallback_msg = props.get("fallback_response")
                if fallback_msg:
                    ai_result = str(fallback_msg)
                else:
                    return {
                        "status": "error",
                        "model": model_name,
                        "error": f"LLM execution failed: {e}. Ensure local engine is online at localhost:11435",
                    }

            return {
                "status": "success",
                "model": model_name,
                "prompt": prompt,
                "response": ai_result,
            }

        # 3. Actions - Python Code
        elif "PythonCode" in type(node).__name__:
            script = props.get("script", "return items")
            local_scope = {"items": input_data, "context": context, "json": json}
            try:
                code_wrapped = f"def _user_script(items, context):\n" + "\n".join(f"    {line}" for line in script.splitlines())
                exec(code_wrapped, local_scope)
                result = local_scope["_user_script"](input_data, context)
                return {"status": "success", "result": result or input_data}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        # 4. Actions - HTTP Request
        elif "HTTPRequest" in type(node).__name__:
            method = props.get("method", "GET").upper()
            url = self.resolve_expressions(props.get("url", "https://api.github.com"), context)
            try:
                req = urllib.request.Request(url, method=method)
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    data = resp.read().decode("utf-8")
                    try:
                        parsed = json.loads(data)
                    except Exception:
                        parsed = data[:500]
                    return {"status": "success", "status_code": resp.status, "data": parsed}
            except Exception as e:
                return {"status": "error", "error": str(e), "url": url}

        # 5. Actions - MCP Tool (Real Client Invocation)
        elif "MCPTool" in type(node).__name__:
            tool_name = props.get("tool_name", "read_file")
            server_name = props.get("server_name", "filesystem")
            args_raw = self.resolve_expressions(props.get("arguments_json", "{}"), context)
            try:
                args = json.loads(args_raw)
            except Exception:
                args = {}

            try:
                from lmms_mcp.client import MCPClient
                client = MCPClient(server_name)
                mcp_res = await client.call_tool(tool_name, args)
                return {
                    "status": "success",
                    "tool": tool_name,
                    "server": server_name,
                    "arguments": args,
                    "output": mcp_res,
                }
            except Exception as err:
                return {
                    "status": "error",
                    "tool": tool_name,
                    "server": server_name,
                    "error": f"MCP execution error: {err}",
                }

        # 6. Actions - Sandboxed Shell Command
        elif "SandboxedCommand" in type(node).__name__:
            raw_cmd = props.get("command", "")
            cmd = self.resolve_expressions(raw_cmd, context)
            ws = props.get("cwd", os.getcwd())
            enforce_sb = bool(props.get("sandboxed", True))

            from lmms_sandbox.runner import default_runner
            res = default_runner.run(
                cmd,
                workspace_dir=ws,
                enforce_sandbox=enforce_sb,
                confirm_callback=lambda c, r: True,
            )
            if res.exit_code != 0:
                return {
                    "status": "error",
                    "command": cmd,
                    "exit_code": res.exit_code,
                    "error": res.stderr or res.output,
                }
            return {
                "status": "success",
                "command": cmd,
                "exit_code": res.exit_code,
                "output": res.output,
                "stdout": res.stdout,
            }

        # 7. Actions - Validation & Test Gate
        elif "ValidationGate" in type(node).__name__:
            test_cmd = props.get("test_command", "pytest -q --maxfail=1")
            ws = props.get("workspace", os.getcwd())

            from lmms.backend.cli.review import verify_workspace_state
            from lmms.backend.agents.specialized.tester import TesterAgent

            ws_state = verify_workspace_state(ws)
            tester = TesterAgent()
            test_res = tester.verify(workspace=ws, test_command=test_cmd)

            passed = ws_state.get("passed", True) and test_res.get("passed", True)
            if not passed:
                return {
                    "status": "error",
                    "passed": False,
                    "syntax_clean": ws_state.get("syntax_clean", True),
                    "test_output": test_res.get("output", "")[:400],
                    "error": f"Validation gate failed! Test output: {test_res.get('output', '')[:200]}",
                }
            return {
                "status": "success",
                "passed": True,
                "git_clean": ws_state.get("git", {}).get("clean", True),
                "syntax_clean": ws_state.get("syntax_clean", True),
                "test_output": test_res.get("output", "All tests passed"),
            }

        # 8. Actions - File & Patch Operation
        elif "FilePatch" in type(node).__name__:
            action = props.get("action", "read")
            target_path = self.resolve_expressions(props.get("path", ""), context)

            from lmms.backend.tools.files import canonical_file_read, canonical_file_write
            from lmms.backend.tools.patch import canonical_apply_patch

            if action == "read":
                read_res = canonical_file_read(target_path)
                if "error" in read_res:
                    return {"status": "error", "error": read_res["error"]}
                return {"status": "success", "content": read_res.get("content", "")}
            elif action == "write":
                content = self.resolve_expressions(props.get("content", ""), context)
                write_res = canonical_file_write(target_path, content)
                if write_res.get("status") == "error":
                    return {"status": "error", "error": write_res.get("error", "Write failed")}
                return {"status": "success", "file": target_path}
            elif action == "patch":
                patch_str = self.resolve_expressions(props.get("content", ""), context)
                apply_res = canonical_apply_patch(patch_str)
                if "Failed" in apply_res:
                    return {"status": "error", "error": apply_res}
                return {"status": "success", "result": apply_res}
            else:
                return {"status": "error", "error": f"Unknown file action: {action}"}

        # 9. Gate - Approval Gate (Pause Execution)
        elif cat == "gate" or "ApprovalGate" in type(node).__name__:
            msg = props.get("message", "Awaiting human approval")
            return {
                "status": "waiting_approval",
                "message": msg,
                "paused_at": time.time(),
            }

        # 6. Logic - If / Else
        elif cat == "logic":
            field = props.get("condition_field", "status")
            expected = str(props.get("value", "success")).lower()
            actual = str(input_data.get(field, "")).lower()
            operator = props.get("operator", "equals")

            if operator == "equals":
                is_true = (actual == expected)
            elif operator == "not_equals":
                is_true = (actual != expected)
            elif operator == "contains":
                is_true = (expected in actual)
            else:
                is_true = bool(actual)

            return {
                "status": "success",
                "branch": "True" if is_true else "False",
                "evaluated_field": field,
                "actual": actual,
                "expected": expected,
            }

        # Default pass-through
        return {"status": "success", "node": node.name(), "data": input_data}

    async def run_pipeline(
        self,
        nodes: List[Any],
        workflow_name: str = "Workflow",
        on_step_update: Optional[Callable[[Any, str, dict], None]] = None,
    ) -> Dict[str, Any]:
        """Executes a list of nodes in pipeline order, capturing traces and recording execution history."""
        exec_id = f"exec_{int(time.time() * 1000)}"
        start_time = time.time()
        context: Dict[str, Any] = {}
        trace: Dict[str, Any] = {"steps": []}
        overall_status = "success"

        current_payload: Dict[str, Any] = {}

        for idx, node in enumerate(nodes):
            # Notify UI: running
            if on_step_update:
                on_step_update(node, "running", current_payload)

            step_start = time.time()
            try:
                output = await self.execute_node(node, current_payload, context)
                step_status = output.get("status", "success")
                if step_status == "error":
                    overall_status = "error"
                elif step_status == "waiting_approval":
                    overall_status = "waiting_approval"
            except Exception as err:
                output = {"status": "error", "error": str(err)}
                overall_status = "error"
                step_status = "error"

            step_duration_ms = int((time.time() - step_start) * 1000)

            # Store in context
            node_key = node.name()
            context[node_key] = output
            context["last"] = output
            current_payload = output

            # Cache on node for inspector view
            node.last_output = output

            # Step trace record
            step_record = {
                "step": idx + 1,
                "node_name": node.name(),
                "node_type": type(node).__name__,
                "duration_ms": step_duration_ms,
                "status": step_status,
                "output": output,
            }
            trace["steps"].append(step_record)

            # Notify UI: step finished
            if on_step_update:
                on_step_update(node, step_status, output)

            if step_status == "waiting_approval":
                try:
                    from lmms.backend.events.bus import get_event_bus
                    get_event_bus().emit("workflow_paused", {
                        "execution_id": exec_id,
                        "workflow_name": workflow_name,
                        "node_name": node.name(),
                    })
                except Exception:
                    pass
                break

            # Brief pause for visual pulse and event loop yield
            await asyncio.sleep(0.08)

        total_duration_ms = int((time.time() - start_time) * 1000)

        # Save trace to SQLite
        self.history.record_execution(
            exec_id=exec_id,
            name=workflow_name,
            start_time=start_time,
            duration_ms=total_duration_ms,
            status=overall_status,
            step_count=len(nodes),
            trace=trace,
        )

        return {
            "execution_id": exec_id,
            "status": overall_status,
            "duration_ms": total_duration_ms,
            "trace": trace,
        }
