from typing import Optional
from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime
from lmms.engine.runtimes.universal_pytorch import UniversalPyTorchRuntime
from lmms.engine.cache_manager import CacheManager
from lmms.engine.air import AirScheduler, RamCache, AirSwapper
import os

class EngineManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if not self._initialized:
            self.runtime = LlamaCppRuntime()
            self.pytorch_runtime = UniversalPyTorchRuntime()
            self.cache = CacheManager()
            self.air_scheduler = AirScheduler()
            self.air_ram_cache = RamCache()
            self.air_swapper = AirSwapper(self.air_scheduler, self.air_ram_cache)
            self._initialized = True

    def get_runtime(self, model_name: str, force_gguf: bool = False):
        if force_gguf or model_name.endswith(".gguf") or (model_name in self.runtime._models) or (model_name + ".gguf" in self.runtime._models):
            return self.runtime
            
        # Check if the file is a local gguf file in the models dir
        models_dir = os.path.expanduser("~/.lmms/models")
        gguf_path = os.path.join(models_dir, f"{model_name}.gguf")
        if os.path.exists(gguf_path):
            return self.runtime

        return self.pytorch_runtime

engine_manager = EngineManager()
