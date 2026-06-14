from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List

class ModelState(QObject):
    """GUI state representing models."""
    models_updated = pyqtSignal(list)
    connection_changed = pyqtSignal(str, str) # model_id, status
    
    def __init__(self):
        super().__init__()
        self._models = []
        self._connected_models = {}
        
    def update_models(self, models: List[Dict[str, Any]]):
        self._models = models
        self.models_updated.emit(models)
        
    def update_connection(self, model_id: str, status: str):
        self._connected_models[model_id] = status
        self.connection_changed.emit(model_id, status)
