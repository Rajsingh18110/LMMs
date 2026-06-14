class TaskDependencyGraph:
    """Evaluates task_dependencies to ensure sequential logic."""
    def __init__(self, db):
        self.db = db

    def add_dependency(self, task_id: str, depends_on_task_id: str):
        self.db.execute("INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
                        (task_id, depends_on_task_id))

    def get_dependencies(self, task_id: str):
        return self.db.fetchall("SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ?", (task_id,))

    def can_start(self, task_id: str) -> bool:
        deps = self.get_dependencies(task_id)
        for dep in deps:
            dep_id = dep['depends_on_task_id']
            row = self.db.fetchone("SELECT status FROM tasks WHERE id = ?", (dep_id,))
            if row and row['status'] != 'Completed':
                return False
        return True
