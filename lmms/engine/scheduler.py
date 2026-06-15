from PyQt6.QtCore import QObject, pyqtSignal, QThread
import time, json
from pathlib import Path

from .cache_manager import CacheManager, CachedModel
from .profiles import ProfileManager
from lmms.core.services.events import EventManager
from lmms.core.services.connection import ConnectionManager

class LoadWorker(QThread):
    """Loads a GGUF model off the UI thread."""
    success = pyqtSignal(str, object)  # model_id, handle
    failure = pyqtSignal(str, str)     # model_id, error_msg

    def __init__(self, model_id: str, path: str,
                 n_gpu_layers: int, n_ctx: int):
        super().__init__()
        self.model_id     = model_id
        self.path         = path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx        = n_ctx

    def run(self):
        try:
            from llama_cpp import Llama
            handle = Llama(
                model_path   = self.path,
                n_gpu_layers = self.n_gpu_layers,
                n_ctx        = self.n_ctx,
                verbose      = False,
                use_mmap     = True,
                use_mlock    = False,
            )
            self.success.emit(self.model_id, handle)
        except Exception as e:
            msg = str(e)
            if "out of memory" in msg.lower() \
                    and self.n_gpu_layers != 0:
                # Auto-retry CPU-only
                self.n_gpu_layers = 0
                self.run()
            else:
                self.failure.emit(self.model_id, msg)


class ModelScheduler(QObject):
    """
    Single entry point for all model operations.
    Coordinates: Registry → CacheManager → Loader → ConnectionManager
    """
    switch_started  = pyqtSignal(str)         # model_id
    switch_done     = pyqtSignal(str, int)    # model_id, ms_taken
    load_failed     = pyqtSignal(str, str)    # model_id, error

    def __init__(self,
                 cache:       CacheManager,
                 profiles:    ProfileManager,
                 events:      EventManager,
                 connections: ConnectionManager):
        super().__init__()
        self._cache       = cache
        self._profiles    = profiles
        self._events      = events
        self._connections = connections
        
        # Load registry from the exact path as requested
        registry_path = Path.home() / ".lmms" / "models.json"
        try:
            if registry_path.exists():
                self._registry = json.loads(registry_path.read_text())
            else:
                self._registry = {}
        except Exception:
            self._registry = {}
            
        self._workers:    dict[str, LoadWorker] = {}

    def request_model(self, model_id: str):
        """Main entry point — ensure model is in VRAM."""
        loc = self._cache.location(model_id)
        self.switch_started.emit(model_id)
        t0 = time.monotonic()

        if loc == "vram":
            self.switch_done.emit(model_id, 0)
            return

        if loc == "ram":
            cached = self._cache.get_ram(model_id)
            self._cache.put_vram(cached)
            ms = int((time.monotonic() - t0) * 1000)
            self.switch_done.emit(model_id, ms)
            self._events.publish("ModelLoaded", 
                                 {"model_id": model_id})
            return

        # Disk → load async
        self._load_from_disk(model_id, t0)

    def _load_from_disk(self, model_id: str, t0: float):
        info    = self._registry.get(model_id, {})
        path    = info.get("path", "")
        profile = self._profiles.for_model(model_id)

        worker = LoadWorker(
            model_id     = model_id,
            path         = path,
            n_gpu_layers = profile.n_gpu_layers,
            n_ctx        = profile.context_len,
        )
        worker.success.connect(
            lambda mid, hdl: self._on_loaded(mid, hdl, t0))
        worker.failure.connect(self._on_failed)
        self._workers[model_id] = worker
        self._connections.connect_model(model_id)  # Equivalent to transition(loading)
        worker.start()

    def _on_loaded(self, model_id: str,
                   handle: object, t0: float):
        info     = self._registry.get(model_id, {})
        size_gb  = info.get("size", 0) / 1e9  # The registry stores "size" usually
        cached   = CachedModel(model_id, handle, size_gb)
        self._cache.put_vram(cached)
        
        ms = int((time.monotonic() - t0) * 1000)
        self.switch_done.emit(model_id, ms)
        self._events.publish("ModelLoaded",
                             {"model_id": model_id, "ms": ms})
        self._workers.pop(model_id, None)

    def _on_failed(self, model_id: str, error: str):
        self._connections.disconnect_model(model_id)  # Clean up the state
        self.load_failed.emit(model_id, error)
        self._events.publish("ModelError",
                             {"model_id": model_id,
                              "error": error})
        self._workers.pop(model_id, None)

    def unload(self, model_id: str):
        evicted = self._cache.evict_vram()
        if evicted and evicted.model_id == model_id:
            del evicted.handle
            import gc; gc.collect()
            self._connections.disconnect_model(model_id)
            self._events.publish("ModelUnloaded",
                                 {"model_id": model_id})
