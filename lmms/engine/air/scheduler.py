import time
from typing import Dict, Any, Optional
from lmms.engine.air.loader import AirLoader
from lmms.engine.air.pager import AirPager

class AirScheduler:
    def __init__(self):
        # Tracker for models managed by Air
        self.active_models: Dict[str, Dict[str, Any]] = {}
        self.groups: Dict[int, Dict[str, str]] = {}
        self.loader = AirLoader()
        self.pager = AirPager()

    def parse_input_and_create_group(self, group_id: int, config_string: str):
        """Parse role pairing such as 'text:qwen2.5-1.5b-instruct-q5_k_m image:llava'."""
        parts = config_string.split()
        mapping = {}
        for part in parts:
            if ":" in part:
                role, m_name = part.split(":", 1)
                mapping[role] = m_name
            else:
                mapping["text"] = part
        self.groups[group_id] = mapping

    def route_request(self, group_id: int, target_role: str, messages: list):
        group = self.groups.get(group_id, {})
        model_name = group.get(target_role)
        if not model_name:
            model_name = list(group.values())[0] if group else "default"
            
        profile = self.loader.analyze_model(model_name)
        if not profile:
            raise FileNotFoundError(f"Model '{model_name}' could not be analyzed or found by AirLoader.")
            
        success = self.pager.load(profile)
        if not success:
            raise RuntimeError(f"Failed to load model '{model_name}' into AirPager.")
            
        gpu_l = profile.optimal_gpu_layers if profile.optimal_gpu_layers != -1 else profile.total_layers
        self.register_model(
            model_name=profile.model_name,
            location=f"Dynamic Hybrid (GPU: {gpu_l}L, CPU: {profile.cpu_layers}L)",
            vram_gb=round((gpu_l / max(profile.total_layers, 1)) * profile.size_gb, 2),
            ram_gb=round((profile.cpu_layers / max(profile.total_layers, 1)) * profile.size_gb, 2)
        )
        self.update_state(model_name, "Active Generating")
        return self.pager.execute_stream(messages)

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
