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

"""Workflow persistence and store for LMMs workflow definitions and run history."""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict
from .models import Workflow, WorkflowRun
from .templates import BUILTIN_TEMPLATES, get_builtin_template


class WorkflowStore:
    """Manages reading and writing workflows and execution run records to disk."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self.root = Path(base_dir)
        else:
            self.root = Path.home() / ".lmms" / "workflows"

        self.def_dir = self.root / "definitions"
        self.runs_dir = self.root / "runs"

        self.def_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def list_workflows(self, include_builtins: bool = True) -> List[Dict[str, str]]:
        """Lists metadata of all available workflows (builtin + saved custom)."""
        items: List[Dict[str, str]] = []

        if include_builtins:
            for wid, wf in BUILTIN_TEMPLATES.items():
                items.append({
                    "id": wf.id,
                    "name": wf.name,
                    "description": wf.description,
                    "source": "builtin",
                    "nodes_count": str(len(wf.nodes)),
                })

        for p in self.def_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                items.append({
                    "id": data.get("id", p.stem),
                    "name": data.get("name", p.stem),
                    "description": data.get("description", ""),
                    "source": "custom",
                    "nodes_count": str(len(data.get("nodes", []))),
                })
            except Exception:
                continue

        return items

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Loads a workflow definition by ID, checking custom files first then builtins."""
        custom_file = self.def_dir / f"{workflow_id}.json"
        if custom_file.exists():
            try:
                return Workflow.from_json(custom_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if workflow_id in BUILTIN_TEMPLATES:
            return get_builtin_template(workflow_id)

        return None

    def save_workflow(self, workflow: Workflow) -> Path:
        """Saves a workflow definition to the store."""
        target = self.def_dir / f"{workflow.id}.json"
        target.write_text(workflow.to_json(), encoding="utf-8")
        return target

    def save_run(self, run: WorkflowRun) -> Path:
        """Saves a workflow execution run record."""
        target = self.runs_dir / f"{run.run_id}.json"
        target.write_text(run.to_json(), encoding="utf-8")
        return target

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Loads a workflow execution run by ID."""
        target = self.runs_dir / f"{run_id}.json"
        if target.exists():
            try:
                return WorkflowRun.from_json(target.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def list_runs(self, limit: int = 15) -> List[Dict[str, str]]:
        """Lists recent workflow run executions."""
        runs: List[Dict[str, str]] = []
        files = sorted(self.runs_dir.glob("*.json"), key=os.path.getmtime, reverse=True)

        for p in files[:limit]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                runs.append({
                    "run_id": data.get("run_id", p.stem),
                    "workflow_id": data.get("workflow_id", "unknown"),
                    "status": data.get("status", "unknown"),
                    "start_time": data.get("start_time", ""),
                    "pending_approval": data.get("pending_approval") or "none",
                })
            except Exception:
                continue

        return runs

    def get_pending_run_for_gate(self, node_id: Optional[str] = None) -> Optional[WorkflowRun]:
        """Finds the most recent run waiting for human approval."""
        files = sorted(self.runs_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        for p in files:
            try:
                run = WorkflowRun.from_json(p.read_text(encoding="utf-8"))
                if run.pending_approval:
                    if node_id is None or run.pending_approval == node_id:
                        return run
            except Exception:
                continue
        return None


default_workflow_store = WorkflowStore()
