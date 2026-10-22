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

"""Unit and integration tests for the Apache 2.0 LMMs Workflow Orchestration Engine."""

import asyncio
import json
import pytest
from pathlib import Path
from lmms_workflow.models import (
    NodeType,
    NodeStatus,
    WorkflowNode,
    WorkflowEdge,
    Workflow,
    WorkflowRun,
    NodeExecutionResult,
)
from lmms_workflow.engine import WorkflowEngine
from lmms_workflow.store import WorkflowStore
from lmms_workflow.templates import (
    BUILTIN_TEMPLATES,
    get_builtin_template,
    create_code_review_pipeline,
    create_automated_bug_fixer,
    create_security_audit_pipeline,
)
from lmms_workflow.cli import handle_panel_cli


class TestWorkflowModels:
    """Verifies Pydantic data models and JSON serialization."""

    def test_workflow_node_creation(self):
        node = WorkflowNode(
            id="cmd_1",
            name="Echo Test",
            node_type=NodeType.COMMAND,
            config={"command": "echo 'hello'"},
        )
        assert node.id == "cmd_1"
        assert node.node_type == NodeType.COMMAND
        assert node.config["command"] == "echo 'hello'"

    def test_workflow_serialization(self):
        wf = Workflow(id="test_wf", name="Test Workflow", description="Unit test")
        wf.add_node(
            WorkflowNode(
                id="n1",
                name="Start",
                node_type=NodeType.PYTHON,
                config={"code": "output = 42"},
            )
        )
        wf.add_node(
            WorkflowNode(
                id="n2",
                name="End",
                node_type=NodeType.COMMAND,
                config={"command": "echo done"},
            )
        )
        wf.add_edge("n1", "n2")

        json_str = wf.to_json()
        assert "test_wf" in json_str
        assert "output = 42" in json_str

        loaded = Workflow.from_json(json_str)
        assert loaded.id == "test_wf"
        assert len(loaded.nodes) == 2
        assert len(loaded.edges) == 1
        assert loaded.edges[0].source_node == "n1"
        assert loaded.edges[0].target_node == "n2"


class TestWorkflowEngineExecution:
    """Verifies asynchronous DAG execution, variable interpolation, and branching."""

    def test_python_and_command_nodes_execution(self, tmp_path):
        async def _test():
            wf = Workflow(id="py_cmd_wf", name="Python & Command Test")
            wf.add_node(
                WorkflowNode(
                    id="step1",
                    name="Generate Value",
                    node_type=NodeType.PYTHON,
                    config={"code": "output = {'number': 10 + 5, 'tag': 'alpha'}"},
                )
            )
            wf.add_node(
                WorkflowNode(
                    id="step2",
                    name="Echo Generated Value",
                    node_type=NodeType.COMMAND,
                    config={"command": "echo 'Result is {{ $node[\"step1\"].output[\"tag\"] }}'"},
                )
            )
            wf.add_edge("step1", "step2")

            engine = WorkflowEngine(workspace_root=str(tmp_path))
            run = await engine.execute(wf)

            assert run.status == NodeStatus.SUCCESS
            assert "step1" in run.results
            assert "step2" in run.results
            assert run.results["step1"].status == NodeStatus.SUCCESS
            assert run.results["step1"].output == {"number": 15, "tag": "alpha"}
            assert run.results["step2"].status == NodeStatus.SUCCESS
            assert "Result is alpha" in str(run.results["step2"].output)

        asyncio.run(_test())

    def test_conditional_branching(self, tmp_path):
        async def _test():
            wf = Workflow(id="branching_wf", name="Branching Test")
            wf.add_node(
                WorkflowNode(
                    id="decide",
                    name="Decision Step",
                    node_type=NodeType.PYTHON,
                    config={"code": "output = {'score': 95}"},
                )
            )
            wf.add_node(
                WorkflowNode(
                    id="pass_node",
                    name="Passed Branch",
                    node_type=NodeType.PYTHON,
                    config={"code": "output = 'PASSED'"},
                )
            )
            wf.add_node(
                WorkflowNode(
                    id="fail_node",
                    name="Failed Branch",
                    node_type=NodeType.PYTHON,
                    config={"code": "output = 'FAILED'"},
                )
            )

            wf.add_edge(
                WorkflowEdge(
                    source_node="decide",
                    target_node="pass_node",
                    condition="$node['decide'].output['score'] >= 80",
                )
            )
            wf.add_edge(
                WorkflowEdge(
                    source_node="decide",
                    target_node="fail_node",
                    condition="$node['decide'].output['score'] < 80",
                )
            )

            engine = WorkflowEngine(workspace_root=str(tmp_path))
            run = await engine.execute(wf)

            assert run.status == NodeStatus.SUCCESS
            assert run.results["pass_node"].status == NodeStatus.SUCCESS
            assert run.results["pass_node"].output == "PASSED"
            assert run.results["fail_node"].status == NodeStatus.SKIPPED

        asyncio.run(_test())

    def test_gate_approval_pause_and_resume(self, tmp_path):
        async def _test():
            wf = Workflow(id="gate_wf", name="Approval Gate Test")
            wf.add_node(
                WorkflowNode(
                    id="prepare",
                    name="Preparation Step",
                    node_type=NodeType.PYTHON,
                    config={"code": "output = 'prepared_data'"},
                )
            )
            wf.add_node(
                WorkflowNode(
                    id="safety_gate",
                    name="Admin Gate",
                    node_type=NodeType.GATE,
                    config={"message": "Please review prepared data"},
                )
            )
            wf.add_node(
                WorkflowNode(
                    id="post_gate",
                    name="After Approval Action",
                    node_type=NodeType.PYTHON,
                    config={"code": "output = 'action_completed'"},
                )
            )

            wf.add_edge("prepare", "safety_gate")
            wf.add_edge("safety_gate", "post_gate")

            engine = WorkflowEngine(workspace_root=str(tmp_path))
            initial_run = await engine.execute(wf)

            # Must pause at safety_gate
            assert initial_run.status == NodeStatus.WAITING_APPROVAL
            assert initial_run.pending_approval == "safety_gate"
            assert initial_run.results["safety_gate"].status == NodeStatus.WAITING_APPROVAL
            assert "post_gate" not in initial_run.results

            # Now approve the gate
            resumed_run = await engine.approve_gate(wf, initial_run, "safety_gate", approved=True)
            assert resumed_run.status == NodeStatus.SUCCESS
            assert resumed_run.pending_approval is None
            assert resumed_run.results["safety_gate"].status == NodeStatus.SUCCESS
            assert resumed_run.results["post_gate"].status == NodeStatus.SUCCESS
            assert resumed_run.results["post_gate"].output == "action_completed"

        asyncio.run(_test())

    def test_cycle_detection_error(self, tmp_path):
        async def _test():
            wf = Workflow(id="cyclic_wf", name="Cyclic Test")
            wf.add_node(WorkflowNode(id="n1", name="N1", node_type=NodeType.PYTHON, config={"code": "output = 1"}))
            wf.add_node(WorkflowNode(id="n2", name="N2", node_type=NodeType.PYTHON, config={"code": "output = 2"}))
            wf.add_edge("n1", "n2")
            wf.add_edge("n2", "n1")  # Cycle!

            engine = WorkflowEngine(workspace_root=str(tmp_path))
            with pytest.raises(ValueError, match="Graph contains cycles"):
                await engine.execute(wf)

        asyncio.run(_test())


class TestWorkflowStore:
    """Verifies workflow persistence to filesystem."""

    def test_store_save_and_load(self, tmp_path):
        store = WorkflowStore(base_dir=str(tmp_path))
        wf = Workflow(id="custom_wf_1", name="Custom Workflow One", description="Stored in test")
        wf.add_node(WorkflowNode(id="a", name="A", node_type=NodeType.COMMAND, config={"command": "ls"}))

        store.save_workflow(wf)
        loaded = store.get_workflow("custom_wf_1")
        assert loaded is not None
        assert loaded.id == "custom_wf_1"
        assert loaded.name == "Custom Workflow One"

        workflows = store.list_workflows(include_builtins=True)
        wf_ids = [w["id"] for w in workflows]
        assert "custom_wf_1" in wf_ids
        assert "code_review_pipeline" in wf_ids

    def test_store_run_history(self, tmp_path):
        store = WorkflowStore(base_dir=str(tmp_path))
        run = WorkflowRun(run_id="run_123", workflow_id="custom_wf_1", status=NodeStatus.SUCCESS)
        run.results["a"] = NodeExecutionResult(node_id="a", status=NodeStatus.SUCCESS, output="done")

        store.save_run(run)
        loaded_run = store.get_run("run_123")
        assert loaded_run is not None
        assert loaded_run.run_id == "run_123"
        assert loaded_run.status == NodeStatus.SUCCESS
        assert loaded_run.results["a"].output == "done"


class TestBuiltinTemplates:
    """Verifies predefined workflow templates."""

    def test_template_instantiation(self):
        assert "code_review_pipeline" in BUILTIN_TEMPLATES
        assert "automated_bug_fixer" in BUILTIN_TEMPLATES
        assert "security_audit" in BUILTIN_TEMPLATES

        p1 = get_builtin_template("code_review_pipeline")
        assert len(p1.nodes) == 4
        assert len(p1.edges) == 3

        p2 = get_builtin_template("automated_bug_fixer")
        assert len(p2.nodes) == 4
        assert any(n.node_type == NodeType.GATE for n in p2.nodes.values())

        p3 = get_builtin_template("security_audit")
        assert len(p3.nodes) == 2


class TestPanelCLI:
    """Verifies terminal CLI panel commands."""

    def test_panel_cli_dispatch(self, tmp_path):
        # Should execute cleanly without raising exceptions
        handle_panel_cli([], str(tmp_path))
        handle_panel_cli(["list"], str(tmp_path))
        handle_panel_cli(["runs"], str(tmp_path))
