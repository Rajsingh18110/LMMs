from typing import Protocol, Dict, List, Any
from lmms.backend.contracts.runtime import ModelRuntime

class ProviderContract(Protocol):
    """Protocol for external and local model providers."""
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection and return status/latency."""
        ...
        
    def scan_models(self) -> List[Dict[str, Any]]:
        """Returns a list of Model metadata dicts."""
        ...
        
    def get_runtime(self) -> ModelRuntime:
        """Returns the execution runtime for this provider."""
        ...
