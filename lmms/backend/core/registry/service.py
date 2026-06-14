import os
import json
import time

class RegistryService:
    """
    Manages the persistent state (~/.lmms/models.json) and 
    runtime state (~/.lmms/runtime.json) for the LMMs Operating System.
    """
    def __init__(self, base_dir="~/.lmms"):
        self.base_dir = os.path.expanduser(base_dir)
        self.models_file = os.path.join(self.base_dir, "models.json")
        self.runtime_file = os.path.join(self.base_dir, "runtime.json")
        self._ensure_dirs()
        self._initialize_runtime()

    def _ensure_dirs(self):
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "cache"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, "runtimes"), exist_ok=True)

    def _initialize_runtime(self):
        # Only initialize if the file doesn't exist
        if not os.path.exists(self.runtime_file):
            runtime_state = {
                "loaded_models": {},
                "connected_models": {},
                "active_model": None,
                "gpu_usage": 0,
                "status": "idle"
            }
            self.save_runtime(runtime_state)

    def load_models(self) -> dict:
        if not os.path.exists(self.models_file):
            return {}
        try:
            with open(self.models_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_models(self, data: dict):
        with open(self.models_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def load_runtime(self) -> dict:
        if not os.path.exists(self.runtime_file):
            return {}
        try:
            with open(self.runtime_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_runtime(self, data: dict):
        with open(self.runtime_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def add_model(self, model_id: str, provider: str, path: str, format: str, size: int, source: str, capabilities: list):
        """Adds a model reference to the persistent registry."""
        models = self.load_models()
        models[model_id] = {
            "id": model_id,
            "provider": provider,
            "path": path,
            "format": format,
            "size": size,
            "source": source,
            "capabilities": capabilities,
            "status": "Imported" if "Imported" in source else "Downloaded",
            "last_used": time.time()
        }
        self.save_models(models)

    def remove_model(self, model_id: str):
        models = self.load_models()
        if model_id in models:
            del models[model_id]
            self.save_models(models)

    def get_model(self, model_id: str):
        return self.load_models().get(model_id)

    def update_runtime_state(self, key: str, value):
        state = self.load_runtime()
        state[key] = value
        self.save_runtime(state)
