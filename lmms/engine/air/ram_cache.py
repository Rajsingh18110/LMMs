from typing import Dict, Any

class RamCache:
    def __init__(self):
        # Tracks models staged in system RAM
        self.staged_models: Dict[str, Any] = {}
        
    def stage_model(self, model_name: str, size_gb: float):
        """
        Stages a model in system RAM (e.g. by loading with n_gpu_layers=0 
        or pinning pages).
        """
        self.staged_models[model_name] = {
            "size_gb": size_gb,
            "status": "staged"
        }
        
    def evict_model(self, model_name: str):
        """
        Removes model from RAM Cache (drops back to Disk).
        """
        if model_name in self.staged_models:
            del self.staged_models[model_name]
            
    def get_models(self) -> list:
        return list(self.staged_models.keys())
