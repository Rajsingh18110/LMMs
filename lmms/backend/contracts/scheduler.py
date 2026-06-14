from typing import Protocol, Any, Dict

class SchedulerContract(Protocol):
    """Protocol for queueing and routing tasks to the appropriate loaded model."""
    
    def queue_task(self, model_id: str, task: Dict[str, Any]) -> str:
        """Returns task_id"""
        ...
        
    def get_status(self, task_id: str) -> str:
        ...
        
    def cancel_task(self, task_id: str) -> bool:
        ...
