import time
from typing import Dict, Any

class AirScheduler:
    def __init__(self):
        # Tracker for models managed by Air
        self.active_models: Dict[str, Dict[str, Any]] = {}
        
    def register_model(self, model_name: str, location: str, vram_gb: float, ram_gb: float):
        self.active_models[model_name] = {
            "state": "Loaded",
            "location": location,
            "vram_gb": vram_gb,
            "ram_gb": ram_gb,
            "last_used": time.time()
        }
        
    def update_state(self, model_name: str, state: str):
        if model_name in self.active_models:
            self.active_models[model_name]["state"] = state
            self.active_models[model_name]["last_used"] = time.time()
            
    def remove_model(self, model_name: str):
        if model_name in self.active_models:
            del self.active_models[model_name]
            
    def get_ps(self) -> list:
        res = []
        for name, info in self.active_models.items():
            res.append({
                "model": name,
                "state": info["state"],
                "vram_gb": info["vram_gb"],
                "ram_gb": info["ram_gb"],
                "last_used": info["last_used"]
            })
        return res
