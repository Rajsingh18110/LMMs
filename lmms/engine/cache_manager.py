import gc
import psutil
from typing import Dict, Any, List

try:
    import torch
except ImportError:
    torch = None

class VRAMInsufficientError(Exception):
    pass

def _enforce_poison_pill():
    import sys
    import inspect
    if "ollama" in sys.modules:
        # Only crash if ollama is in the call stack, avoiding Nuitka bundle false-positives
        for frame in inspect.stack():
            if "ollama" in frame.filename:
                raise RuntimeError("POISON PILL: Active 'ollama' usage detected. LMMS is fully native.")
    sys.modules["ollama"] = None

_enforce_poison_pill()

class CacheManager:
    """
    Real VRAM and RAM tracking for the LMMs Engine.
    """
    def __init__(self):
        # We store loaded models here. dict of model_id -> size_gb
        self.loaded_models: Dict[str, float] = {}

    def _get_cuda_info(self) -> tuple[float, float, float]:
        """Returns (total, used, available) in GB for CUDA."""
        if torch and torch.cuda.is_available():
            # For simplicity, we just check device 0
            device = 0
            total_bytes = torch.cuda.get_device_properties(device).total_memory
            used_bytes = torch.cuda.memory_allocated(device)
            # torch.cuda.memory_reserved can also be checked, but we'll use allocated
            # Actually, to get true available VRAM, we should use torch.cuda.mem_get_info()
            try:
                free_bytes, true_total_bytes = torch.cuda.mem_get_info(device)
                used_bytes = true_total_bytes - free_bytes
                total_bytes = true_total_bytes
            except Exception:
                # Fallback if mem_get_info is not available in older torch
                pass
            
            gb = 1024**3
            return total_bytes / gb, used_bytes / gb, (total_bytes - used_bytes) / gb
        return 0.0, 0.0, 0.0

    def _get_ram_info(self) -> tuple[float, float, float]:
        """Returns (total, used, available) in GB for system RAM."""
        mem = psutil.virtual_memory()
        gb = 1024**3
        return mem.total / gb, (mem.total - mem.available) / gb, mem.available / gb

    def get_stats(self) -> Dict[str, Any]:
        """Return real memory statistics and loaded models."""
        if torch and torch.cuda.is_available():
            total, used, available = self._get_cuda_info()
            device_type = "CUDA"
        else:
            total, used, available = self._get_ram_info()
            device_type = "CPU"

        return {
            "device": device_type,
            "total_gb": round(total, 2),
            "used_gb": round(used, 2),
            "available_gb": round(available, 2),
            "loaded_models": list(self.loaded_models.keys())
        }

    def can_fit(self, model_size_gb: float) -> bool:
        """Simple boolean check before loading."""
        if torch and torch.cuda.is_available():
            _, _, available = self._get_cuda_info()
        else:
            _, _, available = self._get_ram_info()
            
        # 0.5 GB safety margin
        return (available - model_size_gb - 0.5) > 0

    def load_model(self, model_name: str, model_size_gb: float):
        """Check memory, load model if fits, else raise VRAMInsufficientError."""
        if not self.can_fit(model_size_gb):
            raise VRAMInsufficientError(
                f"Cannot load {model_name} ({model_size_gb:.2f}GB). Insufficient memory."
            )
        
        self.loaded_models[model_name] = model_size_gb
        # Actual loading logic (e.g. llama_cpp) is handled by the Runtime,
        # but CacheManager records it here.

    def unload_model(self, model_name: str):
        """Completely free memory for a model."""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            
        if torch and torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        gc.collect()

# Singleton instance for CacheManager if needed globally, but usually handled by Engine
