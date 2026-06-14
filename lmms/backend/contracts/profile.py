from typing import Protocol, Any, Dict

class ProfileContract(Protocol):
    """Protocol for hardware and runtime parameter profiles."""
    
    def apply_profile(self, hw_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Takes a HW profile and returns optimized runtime args (e.g. threads, batch_size)."""
        ...
        
    def recommend_settings(self, model_size_mb: int) -> Dict[str, Any]:
        ...
