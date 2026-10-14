from typing import Dict, Any
from lmms.engine.air.scheduler import AirScheduler
try:
    from lmms.backend.logic.manager import backend_manager
except ImportError:
    backend_manager = None

class AirMonitor:
    def __init__(self, scheduler: AirScheduler):
        self.scheduler = scheduler

    def get_full_metrics(self) -> Dict[str, Any]:
        scheduler_metrics = self.scheduler.get_ps() if hasattr(self.scheduler, "get_ps") else {}
        memory_stats = backend_manager.cache.get_stats() if backend_manager and hasattr(backend_manager, "cache") else {}
        
        return {
            "air_mode_active": True,
            "scheduler": scheduler_metrics,
            "hardware": memory_stats,
        }
