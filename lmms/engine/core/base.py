from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class RuntimeContract(ABC):
    """
    Unified Runtime Abstraction Layer.
    All engines (Engine 1: Air+LlamaCpp, Engine 2: Air+PyTorch) must implement this interface.
    """
    
    @abstractmethod
    def load_model(self, model_id: str) -> bool:
        """Load or prepare model for execution."""
        pass
        
    @abstractmethod
    def unload_model(self, model_id: Optional[str] = None) -> bool:
        """Unload active model to free resources."""
        pass
        
    @abstractmethod
    def generate(self, context: Any, stream: bool = False) -> Any:
        """Execute text generation (stream or batch)."""
        pass
        
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Compute text embedding vector."""
        pass
        
    @abstractmethod
    def tokenize(self, text: str) -> List[int]:
        """Convert text to token IDs."""
        pass
        
    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return engine health and telemetry status."""
        pass

    @abstractmethod
    def chat(self, model: str, messages: list, stream: bool = False, options: Optional[dict] = None, **kwargs) -> Any:
        """Chat completion convenience endpoint."""
        pass
