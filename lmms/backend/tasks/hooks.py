class TaskContextProvider:
    """Context Builder Hooks."""
    def __init__(self, task_manager):
        self.manager = task_manager

    def get_active_tasks(self):
        tasks = self.manager.list_tasks()
        return [t for t in tasks if t['status'] in ('Pending', 'In Progress')]

    def get_related_tasks(self):
        pass

    def get_task_dependencies(self):
        pass

    def get_task_memory(self):
        pass
