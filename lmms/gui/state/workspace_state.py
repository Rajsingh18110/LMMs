from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, Optional

class WorkspaceState(QObject):
    """GUI state for Workspace representation."""
    workspace_changed = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self._current_workspace = None
        
    def set_workspace(self, workspace_data: Optional[Dict[str, Any]]):
        self._current_workspace = workspace_data
        self.workspace_changed.emit(workspace_data)
