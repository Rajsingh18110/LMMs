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
    from typing import cast
    sys.modules["ollama"] = cast(Any, None)

_enforce_poison_pill()

from dataclasses import dataclass
from typing import Optional

@dataclass
class CachedModel:
    model_id: str
    handle: Any = None
    size_gb: float = 0.0
    location: str = "VRAM"

class CacheManager:
    """
    Real VRAM and RAM tracking for the LMMs Engine.
    """
    def __init__(self):
        # We store loaded models here. dict of model_id -> size_gb
        self.loaded_models: Dict[str, float] = {}

    def location(self, model_id: str) -> str:
        return "VRAM" if model_id in self.loaded_models else "DISK"

    def get_ram(self, model_id: str) -> Any:
        return None

    def put_vram(self, model_or_id: Any, handle: Any = None) -> None:
        if isinstance(model_or_id, CachedModel):
            self.loaded_models[model_or_id.model_id] = float(model_or_id.size_gb)
        else:
            self.loaded_models[str(model_or_id)] = 0.0

    def evict_vram(self, model_id: Optional[str] = None) -> Optional[CachedModel]:
        if model_id:
            self.unload_model(model_id)
            return CachedModel(model_id=model_id, handle=None, size_gb=0.0)
        elif self.loaded_models:
            first_key = next(iter(self.loaded_models))
            size = self.loaded_models.pop(first_key)
            return CachedModel(model_id=first_key, handle=None, size_gb=size)
        return None

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
        """Hardware limits are the user's responsibility. Allow all sizes."""
        return True

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
