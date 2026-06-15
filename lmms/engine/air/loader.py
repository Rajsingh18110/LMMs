import os
from dataclasses import dataclass
from typing import Optional
from lmms.backend.manager import backend_manager

@dataclass
class ModelProfile:
    model_name: str
    file_path: str
    size_gb: float
    total_layers_est: int
    optimal_gpu_layers: int

class AirLoader:
    def __init__(self, models_dir: str = "~/.lmms/models"):
        self.models_dir = os.path.expanduser(models_dir)

    def analyze_model(self, model_name: str) -> Optional[ModelProfile]:
        path = os.path.join(self.models_dir, f"{model_name}.gguf")
        print(f"[AirLoader] Model: {model_name}")
        if not os.path.exists(path):
            return None
            
        print("[AirLoader] GGUF loaded successfully")
        size_gb = os.path.getsize(path) / (1024**3)
        
        # 1. Total Layers estimation (heterogeneous scaling)
        # Small models (0.5B) have ~24 layers, Medium (7B/8B) have 32-40 layers.
        total_layers = int(max(24, size_gb * 8))
        
        stats = backend_manager.cache.get_stats()
        available_vram = stats.get("available_gb", 0)
        
        # 2. KV Cache and Runtime Overhead estimation
        # Based on reality test: 0.5B had ~1.0GB overhead, 4B had ~2.5GB overhead.
        overhead_gb = max(1.0, size_gb * 0.4)
        
        # Calculate how much VRAM is left for the model weights
        safe_vram = max(0, available_vram - overhead_gb)
        
        if safe_vram >= size_gb:
            n_gpu_layers = -1 # All layers
            cpu_layers = 0
        else:
            ratio = safe_vram / size_gb
            n_gpu_layers = int(total_layers * ratio)
            cpu_layers = total_layers - n_gpu_layers
            
        # CPU-only fallback
        if stats.get("device") == "CPU":
            n_gpu_layers = 0
            cpu_layers = total_layers

        print(f"[AirPlanner] Total layers: {total_layers}")
        print(f"[AirPlanner] Available VRAM: {available_vram}GB")
        print(f"[AirPlanner] Assigned GPU layers: {n_gpu_layers if n_gpu_layers != -1 else total_layers}")
        print(f"[AirPlanner] CPU layers: {cpu_layers}")

        return ModelProfile(
            model_name=model_name,
            file_path=path,
            size_gb=size_gb,
            total_layers_est=total_layers,
            optimal_gpu_layers=n_gpu_layers
        )
