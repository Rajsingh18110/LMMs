import os
import json
from typing import Optional, Any, Dict
from lmms.engine.engine_1_llamacpp import AirLlamaCppRuntime
from lmms.engine.engine_2_pytorch import AirPyTorchRuntime
from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime
from lmms.engine.runtimes.universal_pytorch import UniversalPyTorchRuntime
from lmms.engine.cache_manager import CacheManager
from lmms.engine.air import AirScheduler, RamCache, AirSwapper

class EngineManager:
    """
    Unified Engine Manager for LMMs:
    - Engine 1: Air Engine + Llama.cpp (GGUF High-Throughput & Hybrid Offload)
    - Engine 2: Air Engine + PyTorch (Safetensors, Multimodal & Training)
    - Auto-Dispatcher: Inspects model format, hardware VRAM and routes automatically.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if not self._initialized:
            # Engine 1: Air + Llama.cpp
            self.engine_1 = AirLlamaCppRuntime()
            # Engine 2: Air + PyTorch
            self.engine_2 = AirPyTorchRuntime()
            
            # Backwards compatibility handles
            self.runtime = self.engine_1
            self.pytorch_runtime = self.engine_2
            
            self.cache = CacheManager()
            self.air_scheduler = self.engine_1.scheduler
            self.air_ram_cache = RamCache()
            self.air_swapper = AirSwapper(self.air_scheduler, self.air_ram_cache)
            
            # Active mode: "auto" | "1" (llamacpp) | "2" (pytorch)
            self.active_mode = "auto"
            self._load_saved_mode()
            self._initialized = True

    def _load_saved_mode(self):
        config_path = os.path.expanduser("~/.lmms/config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    saved = data.get("engine_mode")
                    if saved in ["auto", "1", "2", "llamacpp", "pytorch", "air"]:
                        self.active_mode = saved
            except Exception:
                pass

    def set_engine_mode(self, mode: str) -> str:
        norm = mode.lower().strip()
        if norm in ["auto", "smart"]:
            self.active_mode = "auto"
        elif norm in ["1", "llamacpp", "llama", "gguf", "air"]:
            self.active_mode = "1"
        elif norm in ["2", "pytorch", "torch", "enterprise"]:
            self.active_mode = "2"
        else:
            raise ValueError(f"Unknown engine mode '{mode}'. Use 'auto', '1' (Air+LlamaCpp), or '2' (Air+PyTorch).")

        config_path = os.path.expanduser("~/.lmms/config.json")
        try:
            cfg = {}
            if os.path.exists(config_path):
                with open(config_path, "r") as f: cfg = json.load(f)
            cfg["engine_mode"] = self.active_mode
            with open(config_path, "w") as f: json.dump(cfg, f, indent=4)
        except Exception:
            pass

        return self.active_mode

    def get_runtime(self, model_name: str, force_gguf: bool = False):
        # 1. Explicit forced mode
        if self.active_mode == "1":
            return self.engine_1
        elif self.active_mode == "2":
            return self.engine_2

        # 2. Auto-Dispatcher
        if force_gguf or model_name.endswith(".gguf"):
            return self.engine_1

        models_dir = os.path.expanduser("~/.lmms/models")
        gguf_path = os.path.join(models_dir, f"{model_name}.gguf")
        if os.path.exists(gguf_path):
            return self.engine_1

        # Check manifest
        manifest_path = os.path.join(os.path.expanduser("~/.lmms/manifests"), f"{model_name}.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    m = json.load(f)
                    base = m.get("base_model", "")
                    if base.endswith(".gguf") or os.path.exists(os.path.join(models_dir, f"{base}.gguf")):
                        return self.engine_1
            except Exception:
                pass

        # Fallback to Engine 2 (PyTorch) for HuggingFace / Safetensors / Multimodal
        return self.engine_2

    def status(self) -> Dict[str, Any]:
        return {
            "active_mode": self.active_mode,
            "engine_1": self.engine_1.health(),
            "engine_2": self.engine_2.health()
        }

engine_manager = EngineManager()
