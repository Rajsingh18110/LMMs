from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List

class AppState(QObject):
    """Global GUI application state."""
    active_view_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._active_view = "chat"
        
    @property
    def active_view(self) -> str:
        return self._active_view
        
    @active_view.setter
    def active_view(self, view: str):
        if self._active_view != view:
            self._active_view = view
            self.active_view_changed.emit(view)
