import os
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime

from lmms.backend.services.core_services.services.events import EventManager

class TaskManager:
    """
    Facade for the LMMs Task System.
    Handles orchestration of tasks, branches, assignments, and emits events.
    """
    def __init__(self, workspace_path: str, event_manager: EventManager, db):
        self.workspace_path = os.path.abspath(workspace_path)
        self.events = event_manager
        self.db = db

    def create_task(self, title: str, description: str, branch_name: str) -> str:
        task_id = str(uuid.uuid4())
        # Fetch branch_id if available, otherwise mock
        branch_id = "branch_" + branch_name
        self.db.execute(
            "INSERT INTO tasks (id, workspace_id, branch_id, branch_name, title, description, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (task_id, self.workspace_path, branch_id, branch_name, title, description, 'Pending')
        )
        self.events.publish("TaskCreated", {"task_id": task_id, "title": title})
        return task_id

    def list_tasks(self, branch_name: str = None) -> List[dict]:
        if branch_name:
            rows = self.db.fetchall("SELECT * FROM tasks WHERE branch_name = ?", (branch_name,))
        else:
            rows = self.db.fetchall("SELECT * FROM tasks", ())
        return [dict(r) for r in rows]

    def update_task_status(self, task_id: str, status: str):
        self.db.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, datetime.utcnow(), task_id))
        self.events.publish("TaskUpdated", {"task_id": task_id, "status": status})

    def complete_task(self, task_id: str):
        self.db.execute("UPDATE tasks SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?", 
                        ('Completed', datetime.utcnow(), datetime.utcnow(), task_id))
        self.events.publish("TaskCompleted", {"task_id": task_id})

    def block_task(self, task_id: str, reason: str):
        self.db.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", ('Blocked', datetime.utcnow(), task_id))
        # Insert into events
        event_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO task_events (id, task_id, event_type, event_data) VALUES (?, ?, ?, ?)",
                        (event_id, task_id, "TaskBlocked", reason))
        self.events.publish("TaskBlocked", {"task_id": task_id, "reason": reason})

    def get_task(self, task_id: str) -> Optional[dict]:
        row = self.db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if row:
            return dict(row)
        return None

    def summarize_task(self, task_id: str) -> str:
        from lmms.backend.tasks.memory import TaskMemory
        tm = TaskMemory(self.db)
        return tm.summarize_and_store(task_id)
