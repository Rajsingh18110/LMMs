from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List

class TaskState(QObject):
    """GUI state for Task progress."""
    task_added = pyqtSignal(dict)
    task_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self._tasks = {}
        
    def add_task(self, task_id: str, data: Dict[str, Any]):
        self._tasks[task_id] = data
        self.task_added.emit(data)
        
    def update_task(self, task_id: str, data: Dict[str, Any]):
        if task_id in self._tasks:
            self._tasks[task_id].update(data)
            self.task_updated.emit(self._tasks[task_id])
