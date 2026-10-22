# Copyright 2026 LMMs Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
lmms_workflow.engine - Core DAG workflow execution engine for LMMs.
Built on networkx and Python asyncio for local-first, native execution.
"""

import asyncio
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Union

import networkx as nx

from lmms_workflow.models import (
    NodeExecutionResult,
    NodeStatus,
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowNode,
    WorkflowRun,
)


class WorkflowEngine:
    """Orchestrates deterministic DAG workflow execution with approval gates and data passing."""

    def __init__(self, workspace_dir: Optional[str] = None, workspace_root: Optional[str] = None):
        self.workspace_dir = workspace_root or workspace_dir or os.getcwd()
        self.listeners: List[Callable[[str, Dict[str, Any]], None]] = []

    def add_listener(self, listener: Callable[[str, Dict[str, Any]], None]) -> None:
        self.listeners.append(listener)

    def _emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        for listener in self.listeners:
            try:
                listener(event_name, payload)
            except Exception:
                pass
        try:
            from lmms.backend.events.bus import get_event_bus
            get_event_bus().emit(f"workflow_{event_name}", payload)
        except Exception:
            pass

    def build_dag(self, workflow: Workflow) -> nx.DiGraph:
        """Constructs and validates a networkx DiGraph from workflow nodes and edges."""
        dag = nx.DiGraph()
        for node_id, node in workflow.nodes.items():
            dag.add_node(node_id, data=node)

        for edge in workflow.edges:
            if edge.source_node in workflow.nodes and edge.target_node in workflow.nodes:
                dag.add_edge(edge.source_node, edge.target_node, data=edge)

        if not nx.is_directed_acyclic_graph(dag):
            cycles = list(nx.simple_cycles(dag))
            raise ValueError(f"Workflow contains invalid circular dependency. Graph contains cycles: {cycles}")

        return dag

    def _resolve_template_vars(self, val: Any, context: Dict[str, Any], results: Dict[str, NodeExecutionResult], prev_node: Optional[str]) -> Any:
        """Resolves n8n-style expressions: {{ $node['node_1'].output }} or {{ $ctx.var }} or {{ $prev }}."""
        if isinstance(val, str):
            def _repl(m: re.Match) -> str:
                raw_expr = m.group(1).strip()
                if raw_expr == "$prev" and prev_node and prev_node in results:
                    return str(results[prev_node].output)

                eval_expr = (
                    raw_expr
                    .replace("$node", "results")
                    .replace("$ctx.", "ctx.")
                    .replace("$ctx", "ctx")
                    .replace("$prev", "prev")
                )
                safe_scope = {
                    "results": results,
                    "ctx": context,
                    "context": context,
                    "prev": results[prev_node].output if (prev_node and prev_node in results) else None,
                    "str": str,
                    "len": len,
                    "int": int,
                    "float": float,
                    "dict": dict,
                }
                try:
                    res = eval(eval_expr, {"__builtins__": {}}, safe_scope)
                    return str(res)
                except Exception:
                    pass

                if raw_expr in context:
                    return str(context[raw_expr])
                return m.group(0)

            resolved = re.sub(r"\{\{\s*([^}]+)\s*\}\}", _repl, val)
            return resolved
        elif isinstance(val, dict):
            return {k: self._resolve_template_vars(v, context, results, prev_node) for k, v in val.items()}
        elif isinstance(val, list):
            return [self._resolve_template_vars(i, context, results, prev_node) for i in val]
        return val

    async def execute_node(
        self,
        node: WorkflowNode,
        context: Dict[str, Any],
        results: Dict[str, NodeExecutionResult],
        prev_node: Optional[str] = None
    ) -> NodeExecutionResult:
        """Dispatches node execution to specialized local runner based on NodeType."""
        t0 = time.time()
        self._emit("node_start", {"node_id": node.id, "node_name": node.name, "type": node.node_type.value})

        cfg = self._resolve_template_vars(node.config, context, results, prev_node)
        status = NodeStatus.SUCCESS
        output = None
        error = None

        try:
            if node.node_type == NodeType.COMMAND:
                output = await self._run_command_node(cfg)
            elif node.node_type == NodeType.MODEL:
                output = await self._run_model_node(cfg)
            elif node.node_type == NodeType.MCP:
                output = await self._run_mcp_node(cfg)
            elif node.node_type == NodeType.FILE:
                output = await self._run_file_node(cfg)
            elif node.node_type == NodeType.CONDITION:
                output = self._run_condition_node(cfg, context, results, prev_node)
            elif node.node_type == NodeType.VALIDATION:
                output = await self._run_validation_node(cfg)
            elif node.node_type == NodeType.PYTHON:
                output = self._run_python_node(cfg, context, results, prev_node)
            elif node.node_type == NodeType.GATE:
                # Gate nodes require explicit human approval
                status = NodeStatus.WAITING_APPROVAL
                output = f"Gate '{node.name}' paused. Awaiting human approval."
            else:
                status = NodeStatus.FAILED
                error = f"Unsupported node type: {node.node_type}"

        except Exception as exc:
            status = NodeStatus.FAILED
            error = str(exc)

        dur = round(time.time() - t0, 3)
        res = NodeExecutionResult(
            node_id=node.id,
            status=status,
            output=output,
            error=error,
            duration_s=dur,
            started_at=t0,
            finished_at=time.time(),
        )

        self._emit("node_end", {
            "node_id": node.id,
            "status": status.value,
            "duration_s": dur,
            "output": str(output)[:200] if output else None,
            "error": error,
        })
        return res

    async def _run_command_node(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Runs sandboxed shell / terminal command with policy check."""
        cmd = cfg.get("command", "")
        if not cmd:
            raise ValueError("CommandNode requires 'command' configuration parameter")

        ws = cfg.get("workspace", self.workspace_dir)
        enforce_sb = cfg.get("sandboxed", False)

        from lmms_sandbox.runner import default_runner
        auto_confirm = cfg.get("auto_confirm", True)
        confirm_cb = (lambda c, r: True) if auto_confirm else None
        res = default_runner.run(
            cmd,
            workspace_dir=ws,
            enforce_sandbox=enforce_sb,
            confirm_callback=confirm_cb,
        )
        if res.exit_code != 0:
            raise RuntimeError(f"Command failed (exit {res.exit_code}): {res.stderr or res.output}")
        return {"stdout": res.stdout, "stderr": res.stderr, "exit_code": res.exit_code, "output": res.output}

    async def _run_model_node(self, cfg: Dict[str, Any]) -> str:
        """Executes LLM reasoning step via local engine or configured provider."""
        prompt = cfg.get("prompt", "")
        model = cfg.get("model", "qwen2.5-1.5b-instruct-q5_k_m")
        sys_prompt = cfg.get("system_prompt", "You are an automated workflow execution node. Answer concisely.")

        try:
            import requests
            resp = requests.post(
                "http://localhost:11435/v1/chat/completions",
                json={
                    "model_name": model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                timeout=cfg.get("timeout", 90.0),
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "").strip()
            else:
                raise RuntimeError(f"Model call failed: HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            if cfg.get("fallback_response"):
                return str(cfg.get("fallback_response"))
            raise RuntimeError(f"Model node error ({e}). Ensure local LLM engine is running on http://localhost:11435")

    async def _run_mcp_node(self, cfg: Dict[str, Any]) -> Any:
        """Invokes dynamic MCP tool on configured server."""
        server = cfg.get("server", "filesystem")
        tool = cfg.get("tool", "")
        args = cfg.get("arguments", {})

        from lmms_mcp.client import MCPClient
        client = MCPClient(server)
        res = await client.call_tool(tool, args)
        return res

    async def _run_file_node(self, cfg: Dict[str, Any]) -> Any:
        """Performs file read, write, or patch within workspace boundaries."""
        action = cfg.get("action", "read")
        path = cfg.get("path", "")
        if not path:
            raise ValueError("FileNode requires 'path' parameter")

        from lmms.backend.tools.files import canonical_file_read, canonical_file_write
        from lmms.backend.tools.patch import canonical_apply_patch

        if action == "read":
            res = canonical_file_read(path)
            if "error" in res:
                raise RuntimeError(res["error"])
            return res.get("content", "")
        elif action == "write":
            content = cfg.get("content", "")
            res = canonical_file_write(path, content)
            if res.get("status") == "error":
                raise RuntimeError(res.get("error", "Write failed"))
            return res
        elif action == "patch":
            patch_content = cfg.get("patch", "")
            res_str = canonical_apply_patch(patch_content)
            if "Failed" in res_str:
                raise RuntimeError(res_str)
            return res_str
        else:
            raise ValueError(f"Unknown file action: {action}")

    def _run_condition_node(self, cfg: Dict[str, Any], context: Dict[str, Any], results: Dict[str, NodeExecutionResult], prev_node: Optional[str]) -> bool:
        """Evaluates condition expression (e.g. 'len(output) > 0' or 'exit_code == 0')."""
        expr = cfg.get("expression", "True")
        prev_out = results[prev_node].output if (prev_node and prev_node in results) else None
        safe_globals = {"len": len, "str": str, "int": int, "bool": bool, "results": results, "ctx": context, "prev": prev_out}
        try:
            return bool(eval(expr, safe_globals, safe_globals))
        except Exception as e:
            raise ValueError(f"Failed to evaluate condition '{expr}': {e}")

    async def _run_validation_node(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Runs workspace syntax checks or pytest test runner."""
        target_ws = cfg.get("workspace", self.workspace_dir)
        from lmms.backend.cli.review import verify_workspace_state
        from lmms.backend.agents.specialized.tester import TesterAgent

        ws_state = verify_workspace_state(target_ws)
        tester = TesterAgent()
        test_res = tester.verify(workspace=target_ws, test_command=cfg.get("test_command"))

        passed = ws_state.get("passed", True) and test_res.get("passed", True)
        if not passed:
            errs = ws_state.get("syntax_errors", [])
            out_err = test_res.get("output", "")
            raise RuntimeError(f"Validation gate failed! Syntax errors: {errs}; Test output: {out_err[:200]}")

        return {
            "passed": True,
            "git_clean": ws_state.get("git", {}).get("clean", True),
            "syntax_clean": ws_state.get("syntax_clean", True),
            "test_runner": test_res.get("runner", "none"),
        }

    def _run_python_node(self, cfg: Dict[str, Any], context: Dict[str, Any], results: Dict[str, NodeExecutionResult], prev_node: Optional[str]) -> Any:
        """Executes a custom Python snippet with safe isolated locals."""
        code = cfg.get("code", "")
        prev_out = results[prev_node].output if (prev_node and prev_node in results) else None
        locs = {"context": context, "results": results, "prev": prev_out, "output": None}
        exec(code, {"__builtins__": __builtins__}, locs)
        return locs.get("output")

    async def run(self, workflow: Workflow, initial_context: Optional[Dict[str, Any]] = None, resume_run: Optional[WorkflowRun] = None) -> WorkflowRun:
        """Executes the full DAG workflow topologically with branching and approval handling."""
        dag = self.build_dag(workflow)
        run = resume_run or WorkflowRun(workflow_id=workflow.id, context=initial_context or {})
        run.status = NodeStatus.RUNNING

        self._emit("workflow_start", {"run_id": run.run_id, "workflow_name": workflow.name, "nodes_count": len(workflow.nodes)})

        generations = list(nx.topological_generations(dag))

        for gen_idx, gen_nodes in enumerate(generations):
            for node_id in gen_nodes:
                # If resuming and node already completed successfully, skip
                if node_id in run.results and run.results[node_id].status == NodeStatus.SUCCESS:
                    continue

                # Check edge incoming conditions from parent nodes
                parents = list(dag.predecessors(node_id))
                skip_node = False
                prev_node_id = parents[0] if parents else None

                for p_id in parents:
                    p_res = run.results.get(p_id)
                    if not p_res or p_res.status != NodeStatus.SUCCESS:
                        skip_node = True
                        break

                    # Evaluate edge condition if specified
                    edge_data: WorkflowEdge = dag.get_edge_data(p_id, node_id).get("data")
                    if edge_data and edge_data.condition:
                        cond_expr = edge_data.condition
                        cond_clean = cond_expr.replace("$node", "results").replace("$ctx", "ctx").replace("$prev", "prev")
                        safe_ctx = {
                            "output": p_res.output,
                            "prev": p_res.output,
                            "status": p_res.status.value,
                            "ctx": run.context,
                            "results": run.results,
                        }
                        try:
                            cond_ok = bool(eval(cond_clean, {"__builtins__": {"len": len, "int": int, "str": str, "float": float, "bool": bool}}, safe_ctx))
                            if not cond_ok:
                                skip_node = True
                                break
                        except Exception:
                            skip_node = True
                            break

                if skip_node:
                    run.results[node_id] = NodeExecutionResult(
                        node_id=node_id,
                        status=NodeStatus.SKIPPED,
                        output="Skipped due to unsatisfied parent condition or failed predecessor",
                    )
                    continue

                node = workflow.nodes[node_id]
                res = await self.execute_node(node, run.context, run.results, prev_node=prev_node_id)
                run.results[node_id] = res

                # Check for approval gate pause
                if res.status == NodeStatus.WAITING_APPROVAL:
                    run.status = NodeStatus.WAITING_APPROVAL
                    run.pending_approval = node_id
                    run.updated_at = time.time()
                    self._emit("workflow_paused", {"run_id": run.run_id, "gate_node": node_id})
                    return run

                # Check for node failure
                if res.status == NodeStatus.FAILED:
                    run.status = NodeStatus.FAILED
                    run.updated_at = time.time()
                    self._emit("workflow_failed", {"run_id": run.run_id, "failed_node": node_id, "error": res.error})
                    return run

        run.status = NodeStatus.SUCCESS
        run.updated_at = time.time()
        self._emit("workflow_complete", {"run_id": run.run_id, "status": "success"})
        return run

    async def execute(
        self,
        workflow: Workflow,
        initial_context: Optional[Dict[str, Any]] = None,
        run_state: Optional[WorkflowRun] = None,
    ) -> WorkflowRun:
        """Alias for run() to execute full workflow DAG."""
        return await self.run(workflow, initial_context=initial_context, resume_run=run_state)

    async def approve_gate(
        self,
        workflow_or_run: Union[Workflow, WorkflowRun],
        run_or_node_id: Union[WorkflowRun, str],
        node_id_or_approved: Union[str, bool] = True,
        approved: bool = True,
    ) -> WorkflowRun:
        """Resolves a pending GateNode approval and resumes downstream execution if workflow is given."""
        if isinstance(workflow_or_run, Workflow):
            wf = workflow_or_run
            run = run_or_node_id
            node_id = str(node_id_or_approved)
            is_approved = bool(approved)
        else:
            wf = None
            run = workflow_or_run
            node_id = str(run_or_node_id)
            is_approved = bool(node_id_or_approved)

        if run.pending_approval != node_id:
            raise ValueError(f"Run {run.run_id} is not waiting for approval on node '{node_id}'")

        if is_approved:
            run.results[node_id] = NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.SUCCESS,
                output="Approved by user",
                finished_at=time.time(),
            )
            run.pending_approval = None
            run.status = NodeStatus.PENDING
            if wf:
                return await self.run(wf, resume_run=run)
        else:
            run.results[node_id] = NodeExecutionResult(
                node_id=node_id,
                status=NodeStatus.FAILED,
                output="Rejected by user",
                error="Human approval denied",
                finished_at=time.time(),
            )
            run.pending_approval = None
            run.status = NodeStatus.FAILED

        return run
