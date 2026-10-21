import os
import json
from typing import Optional, Any, Dict

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
            self._engine_1 = None
            self._engine_2 = None
            self._cache = None
            self._air_ram_cache = None
            self._air_swapper = None
            
            # Active mode: "auto" | "1" (llamacpp) | "2" (pytorch)
            self.active_mode = "auto"
            self._load_saved_mode()
            self._initialized = True

    @property
    def engine_1(self):
        if self._engine_1 is None:
            from lmms.engine.engine_1_llamacpp import AirLlamaCppRuntime
            self._engine_1 = AirLlamaCppRuntime()
        return self._engine_1

    @property
    def runtime(self):
        return self.engine_1

    @property
    def engine_2(self):
        if self._engine_2 is None:
            from lmms.engine.engine_2_pytorch import AirPyTorchRuntime
            self._engine_2 = AirPyTorchRuntime()
        return self._engine_2

    @property
    def pytorch_runtime(self):
        return self.engine_2

    @property
    def cache(self):
        if self._cache is None:
            from lmms.engine.cache_manager import CacheManager
            self._cache = CacheManager()
        return self._cache

    @property
    def air_scheduler(self):
        return self.engine_1.scheduler

    @property
    def air_ram_cache(self):
        if self._air_ram_cache is None:
            from lmms.engine.air import RamCache
            self._air_ram_cache = RamCache()
        return self._air_ram_cache

    @property
    def air_swapper(self):
        if self._air_swapper is None:
            from lmms.engine.air import AirSwapper
            self._air_swapper = AirSwapper(self.air_scheduler, self.air_ram_cache)
        return self._air_swapper

    def _load_saved_mode(self):
        config_path = os.path.expanduser("~/.lmms/config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    saved = data.get("engine_mode")
                    if saved in ["auto", "1", "2", "3", "llamacpp", "pytorch", "air", "unified", "super"]:
                        if saved in ["3", "unified", "super"]:
                            self.active_mode = "auto"
                        else:
                            self.active_mode = saved
            except Exception:
                pass

    def get_tier_info(self) -> Dict[str, Any]:
        """Returns structured information about current engine tier."""
        if self.active_mode == "1":
            return {
                "tier": 1,
                "name": "Tier 1: llama.cpp + AirEngine",
                "description": "GGUF High-Throughput & Hybrid Offload Engine",
                "active_mode": "1"
            }
        elif self.active_mode == "2":
            return {
                "tier": 2,
                "name": "Tier 2: PyTorch + AirEngine",
                "description": "Safetensors, HuggingFace Multimodal & Fine-Tuning Node",
                "active_mode": "2"
            }
        else:
            return {
                "tier": 3,
                "name": "Tier 3: Unified Super Engine (llama.cpp + PyTorch + AirEngine)",
                "description": "3-in-1 Super Engine with Auto-Dispatching & Unified RAM/VRAM Caching",
                "active_mode": "auto"
            }

    def set_engine_mode(self, mode: str) -> str:
        norm = str(mode).lower().strip()
        if norm in ["auto", "smart", "3", "tier3", "unified", "super", "all", "3-in-1"]:
            self.active_mode = "auto"
        elif norm in ["1", "tier1", "llamacpp", "llama", "gguf", "air"]:
            self.active_mode = "1"
        elif norm in ["2", "tier2", "pytorch", "torch", "enterprise"]:
            self.active_mode = "2"
        else:
            raise ValueError(f"Unknown engine mode '{mode}'. Use '1' (Tier 1: Air+LlamaCpp), '2' (Tier 2: Air+PyTorch), or '3' / 'auto' (Tier 3: Unified 3-in-1 Super Engine).")

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

    def get_loaded_models(self) -> Dict[str, Any]:
        """Returns unified dictionary of all currently loaded models across both engines."""
        models: Dict[str, Any] = {}
        if self._engine_1 is not None and hasattr(self._engine_1, "_models") and isinstance(self._engine_1._models, dict):
            models.update(self._engine_1._models)
        if self._engine_2 is not None and hasattr(self._engine_2, "_models") and isinstance(self._engine_2._models, dict):
            models.update(self._engine_2._models)
        return models

    def is_model_loaded(self, model_name: str) -> bool:
        loaded = self.get_loaded_models()
        clean = os.path.splitext(os.path.basename(model_name))[0].lower()
        if model_name in loaded or f"{model_name}.gguf" in loaded or clean in [k.lower() for k in loaded]:
            return True
        for k in loaded.keys():
            if os.path.splitext(os.path.basename(k))[0].lower() == clean:
                return True
        if self._engine_1 is not None and hasattr(self._engine_1, "scheduler"):
            if self._engine_1.scheduler.is_model_active(model_name):
                return True
        return False

    def unload_all(self):
        if self._engine_1 is not None and hasattr(self._engine_1, "unload_model"):
            try:
                self._engine_1.unload_model()
            except Exception:
                pass
        if self._engine_2 is not None and hasattr(self._engine_2, "unload_model"):
            try:
                self._engine_2.unload_model()
            except Exception:
                pass

    def status(self) -> Dict[str, Any]:
        return {
            "active_mode": self.active_mode,
            "engine_1": self._engine_1.health() if self._engine_1 is not None else {"status": "idle"},
            "engine_2": self._engine_2.health() if self._engine_2 is not None else {"status": "idle"},
            "loaded_models": list(self.get_loaded_models().keys())
        }

engine_manager = EngineManager()
