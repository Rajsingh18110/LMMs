from typing import Protocol, Any, Dict, List, Optional

class MemoryContract(Protocol):
    """Protocol for vector databases and memory providers."""
    
    def add_document(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        ...
        
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        ...
        
    def clear(self) -> None:
        ...
