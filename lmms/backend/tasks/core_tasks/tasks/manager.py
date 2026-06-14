from .task import Task, TaskStatus
import uuid
import datetime

class TaskManager:
    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def create(self, title: str, 
               description: str) -> Task:
        task_id = str(uuid.uuid4())
        t = Task(id=task_id, title=title, description=description)
        self._tasks[task_id] = t
        return t

    def update_status(self, task_id: str,
                      status: TaskStatus):
        t = self.get_by_id(task_id)
        if t:
            t.status = status
            t.updated_at = datetime.datetime.now().isoformat()

    def add_subtask(self, parent_id: str,
                    subtask: Task):
        t = self.get_by_id(parent_id)
        if t:
            subtask.parent_id = parent_id
            t.subtasks.append(subtask)
            self._tasks[subtask.id] = subtask
            t.updated_at = datetime.datetime.now().isoformat()

    def get_pending(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_by_id(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)
