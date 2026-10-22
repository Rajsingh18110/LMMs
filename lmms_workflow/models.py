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

"""Data models for lmms_workflow orchestration engine."""

import datetime
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    MODEL = "model"
    COMMAND = "command"
    MCP = "mcp"
    FILE = "file"
    GATE = "gate"
    CONDITION = "condition"
    VALIDATION = "validation"
    PYTHON = "python"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_APPROVAL = "waiting_approval"


class WorkflowEdge(BaseModel):
    source_node: str
    target_node: str
    condition: Optional[str] = None  # e.g. "outcome == 'success'" or "exit_code == 0"
    source_handle: Optional[str] = "default"
    target_handle: Optional[str] = "default"


class WorkflowNode(BaseModel):
    id: str
    name: str
    node_type: NodeType
    config: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    timeout: float = 120.0
    description: Optional[str] = None


class NodeExecutionResult(BaseModel):
    node_id: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    duration_s: float = 0.0
    started_at: float = Field(default_factory=time.time)
    finished_at: float = Field(default_factory=time.time)

    @property
    def duration_ms(self) -> float:
        return self.duration_s * 1000.0


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    nodes: Dict[str, WorkflowNode] = Field(default_factory=dict)
    edges: List[WorkflowEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def add_node(self, node: WorkflowNode) -> "Workflow":
        self.nodes[node.id] = node
        return self

    def add_edge(
        self,
        source_or_edge: Union[WorkflowEdge, str],
        target: Optional[str] = None,
        condition: Optional[str] = None,
    ) -> "Workflow":
        if isinstance(source_or_edge, WorkflowEdge):
            self.edges.append(source_or_edge)
        else:
            self.edges.append(
                WorkflowEdge(
                    source_node=str(source_or_edge),
                    target_node=str(target),
                    condition=condition,
                )
            )
        return self

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Workflow":
        return cls.model_validate_json(json_str)


class WorkflowRun(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    workflow_id: str
    status: NodeStatus = NodeStatus.PENDING
    results: Dict[str, NodeExecutionResult] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    pending_approval: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    @property
    def start_time(self) -> str:
        return datetime.datetime.fromtimestamp(self.created_at).isoformat()

    @property
    def end_time(self) -> Optional[str]:
        if self.updated_at and self.status in (NodeStatus.SUCCESS, NodeStatus.FAILED):
            return datetime.datetime.fromtimestamp(self.updated_at).isoformat()
        return None

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "WorkflowRun":
        return cls.model_validate_json(json_str)
