import time
from typing import Dict
from lmms.core.services.registry import RegistryService
from lmms.core.services.events import event_bus

class ConnectionManager:
    """
    Manages the exact lifecycle state of models.
    States: Remote -> Downloaded -> Imported -> Connected -> Loaded -> Running -> Idle -> Unloading -> Error
    """
    def __init__(self, registry: RegistryService):
        self.registry = registry

    def connect_model(self, model_id: str) -> bool:
        """Sets a model as connected and updates runtime."""
        model = self.registry.get_model(model_id)
        if not model:
            return False

        runtime = self.registry.load_runtime()
        connected = runtime.get("connected_models", {})
        
        if model_id not in connected:
            connected[model_id] = {
                "state": "Connected",
                "connected_at": time.time()
            }
            runtime["connected_models"] = connected
            self.registry.save_runtime(runtime)
            event_bus.publish("ModelConnected", {"model_id": model_id})
        return True

    def disconnect_model(self, model_id: str) -> bool:
        """Disconnects a model from the active pool."""
        runtime = self.registry.load_runtime()
        connected = runtime.get("connected_models", {})
        
        if model_id in connected:
            del connected[model_id]
            runtime["connected_models"] = connected
            
            if runtime.get("active_model") == model_id:
                runtime["active_model"] = None
                
            self.registry.save_runtime(runtime)
            event_bus.publish("ModelDisconnected", {"model_id": model_id})
            return True
        return False

    def get_connected_models(self) -> Dict:
        """Returns all connected models and their states."""
        runtime = self.registry.load_runtime()
        return runtime.get("connected_models", {})
