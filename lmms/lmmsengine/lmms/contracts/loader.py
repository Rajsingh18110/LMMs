from typing import Protocol, Any, Dict, List

class LoaderContract(Protocol):
    """Protocol for loading models into memory."""
    
    def load(self, path: str, format: str, **kwargs) -> Any:
        ...
        
    def offload(self, loaded_ref: Any) -> bool:
        ...
