from typing import Protocol, Any, Dict

class CacheContract(Protocol):
    """Protocol for KV caching and state management across generation steps."""
    
    def get_cache(self, session_id: str) -> Any:
        ...
        
    def set_cache(self, session_id: str, cache_state: Any) -> bool:
        ...
        
    def clear_cache(self, session_id: str) -> bool:
        ...
