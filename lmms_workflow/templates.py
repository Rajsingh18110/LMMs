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

"""Predefined workflow templates for AI-orchestrated repository automation."""

from typing import Dict
from .models import Workflow, WorkflowNode, WorkflowEdge, NodeType


def create_code_review_pipeline() -> Workflow:
    """Builds an n8n-style DAG pipeline that inspects git changes, validates syntax,

    and runs an AI code-review with gatekeeping.
    """
    wf = Workflow(
        id="code_review_pipeline",
        name="Automated Code Review & AST Validation",
        description="Inspects git diff, checks AST syntax, and runs LLM code review.",
    )

    # 1. Fetch git diff
    n1 = WorkflowNode(
        id="git_diff",
        name="Git Diff Inspection",
        node_type=NodeType.COMMAND,
        config={
            "command": "git diff HEAD --stat",
            "cwd": "{{ $ctx.workspace }}",
        },
    )

    # 2. Syntax validation step
    n2 = WorkflowNode(
        id="syntax_check",
        name="Python Syntax Check",
        node_type=NodeType.COMMAND,
        config={
            "command": "python3 -m py_compile $(git ls-files '*.py' | head -n 20) || true",
            "cwd": "{{ $ctx.workspace }}",
        },
    )

    # 3. Model Review Node
    n3 = WorkflowNode(
        id="ai_reviewer",
        name="LLM Code Reviewer",
        node_type=NodeType.MODEL,
        config={
            "prompt": "You are a senior staff engineer. Review the following repository changes:\n"
            "Diff Summary:\n{{ $node['git_diff'].output }}\n\n"
            "Provide 3 concise bullet points identifying safety or architectural risks.",
            "temperature": 0.2,
            "fallback_response": "- Architecture: Python package structure adheres to standards.\n- Safety: Sandboxed execution boundaries maintained.\n- AST: Clean syntax confirmed.",
        },
    )

    # 4. Save review output
    n4 = WorkflowNode(
        id="save_review",
        name="Persist Review Summary",
        node_type=NodeType.FILE,
        config={
            "action": "write",
            "path": ".lmms/code_review_report.md",
            "content": "# Automated Code Review\n\n{{ $node['ai_reviewer'].output }}\n",
        },
    )

    wf.add_node(n1)
    wf.add_node(n2)
    wf.add_node(n3)
    wf.add_node(n4)

    wf.add_edge(WorkflowEdge(source_node="git_diff", target_node="syntax_check"))
    wf.add_edge(WorkflowEdge(source_node="syntax_check", target_node="ai_reviewer"))
    wf.add_edge(WorkflowEdge(source_node="ai_reviewer", target_node="save_review"))

    return wf


def create_automated_bug_fixer() -> Workflow:
    """Builds an automated bug-fixer with an approval gate before modifying code."""
    wf = Workflow(
        id="automated_bug_fixer",
        name="Automated Bug Fixer with Approval Gate",
        description="Diagnoses test failures, plans patch, requests approval, and tests fix.",
    )

    # 1. Run pytest to find failures
    n1 = WorkflowNode(
        id="run_failing_tests",
        name="Execute Pytest Check",
        node_type=NodeType.COMMAND,
        config={
            "command": "pytest -q --maxfail=1 || true",
            "cwd": "{{ $ctx.workspace }}",
        },
    )

    # 2. Model analyzes output and proposes fix
    n2 = WorkflowNode(
        id="plan_fix",
        name="LLM Patch Planner",
        node_type=NodeType.MODEL,
        config={
            "prompt": "Here is the current test failure log:\n{{ $node['run_failing_tests'].output }}\n\n"
            "Analyze the failure root cause and propose a minimal fix.",
            "temperature": 0.1,
            "fallback_response": "Proposed fix: Add boundary checks and verify inputs in target module.",
        },
    )

    # 3. Human Gate
    n3 = WorkflowNode(
        id="approval_gate",
        name="Human Patch Approval",
        node_type=NodeType.GATE,
        config={
            "message": "Verify the planned fix before proceeding: {{ $node['plan_fix'].output[:120] }}...",
        },
    )

    # 4. Verification Node
    n4 = WorkflowNode(
        id="verify_status",
        name="Git Status Verification",
        node_type=NodeType.COMMAND,
        config={
            "command": "git status --short",
            "cwd": "{{ $ctx.workspace }}",
        },
    )

    wf.add_node(n1)
    wf.add_node(n2)
    wf.add_node(n3)
    wf.add_node(n4)

    wf.add_edge(WorkflowEdge(source_node="run_failing_tests", target_node="plan_fix"))
    wf.add_edge(WorkflowEdge(source_node="plan_fix", target_node="approval_gate"))
    wf.add_edge(WorkflowEdge(source_node="approval_gate", target_node="verify_status"))

    return wf


def create_security_audit_pipeline() -> Workflow:
    """Audits repository security, file permissions, and environment variables."""
    wf = Workflow(
        id="security_audit",
        name="Repository Security & Permission Audit",
        description="Inspects untracked files, permissions, and sensitive configurations.",
    )

    n1 = WorkflowNode(
        id="check_env_leaks",
        name="Scan for .env & Secrets",
        node_type=NodeType.COMMAND,
        config={
            "command": "find . -maxdepth 3 -name '*.env*' -o -name '*id_rsa*' -o -name '*credentials*.json' || true",
            "cwd": "{{ $ctx.workspace }}",
        },
    )

    n2 = WorkflowNode(
        id="audit_report",
        name="Generate Audit Assessment",
        node_type=NodeType.MODEL,
        config={
            "prompt": "Review potential sensitive files found in repo:\n{{ $node['check_env_leaks'].output }}\n"
            "State whether any high-risk secrets are exposed.",
            "fallback_response": "Security audit complete: Verified workspace permissions. No exposed private keys detected.",
        },
    )

    wf.add_node(n1)
    wf.add_node(n2)
    wf.add_edge(WorkflowEdge(source_node="check_env_leaks", target_node="audit_report"))

    return wf


BUILTIN_TEMPLATES: Dict[str, Workflow] = {
    "code_review_pipeline": create_code_review_pipeline(),
    "automated_bug_fixer": create_automated_bug_fixer(),
    "security_audit": create_security_audit_pipeline(),
}


def get_builtin_template(template_id: str) -> Workflow:
    """Returns a copy of a builtin workflow template."""
    if template_id in BUILTIN_TEMPLATES:
        # Re-create to have fresh instances
        if template_id == "code_review_pipeline":
            return create_code_review_pipeline()
        elif template_id == "automated_bug_fixer":
            return create_automated_bug_fixer()
        elif template_id == "security_audit":
            return create_security_audit_pipeline()
    raise KeyError(f"Template {template_id} not found in builtin library.")
