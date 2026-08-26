from PyQt6.QtCore import QObject
from .app_state import AppState
from .workspace_state import WorkspaceState
from .model_state import ModelState
from .task_state import TaskState
from lmms.backend.logic.manager import BackendManager

class GUIStateManager(QObject):
    """
    Central state manager for the GUI.
    Listens to BackendManager events and updates view states, which emit signals to widgets.
    """
    def __init__(self, backend: BackendManager):
        super().__init__()
        self.backend = backend
        self.app = AppState()
        self.workspace = WorkspaceState()
        self.models = ModelState()
        self.tasks = TaskState()
        
        self._connect_backend_events()
        
    def _connect_backend_events(self):
        # Wire backend event bus to state updates
        self.backend.events.subscribe("ModelImported", self._on_model_imported)
        self.backend.events.subscribe("ModelDownloaded", self._on_model_downloaded)
        self.backend.events.subscribe("ModelConnected", self._on_model_connected)
        
    def _on_model_imported(self, data):
        # Refresh model list
        from lmms.backend.core.registry.model_registry import ModelRegistry
        models_list = ModelRegistry.list()
        self.models.update_models(models_list)
        
    def _on_model_downloaded(self, data):
        # Refresh model list
        from lmms.backend.core.registry.model_registry import ModelRegistry
        models_list = ModelRegistry.list()
        self.models.update_models(models_list)
        
    def _on_model_connected(self, data):
        if "model_id" in data:
            self.models.update_connection(data["model_id"], "Connected")
