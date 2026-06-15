from typing import Dict, Any
from lmms.engine.air.scheduler import AirScheduler
from lmms.backend.manager import backend_manager

class AirMonitor:
    def __init__(self, scheduler: AirScheduler):
        self.scheduler = scheduler

    def get_full_metrics(self) -> Dict[str, Any]:
        scheduler_metrics = self.scheduler.get_metrics()
        memory_stats = backend_manager.cache.get_stats()
        
        return {
            "air_mode_active": True,
            "scheduler": scheduler_metrics,
            "hardware": memory_stats,
            # Throughput requires token tracking which we can add later into the generator hook
        }
