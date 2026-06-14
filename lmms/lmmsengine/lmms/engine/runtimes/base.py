from abc import ABC, abstractmethod
from typing import Dict, Any

class RuntimeContract(ABC):
    """
    Unified Runtime Abstraction Layer.
    All engines (llama.cpp, vLLM, Air) must implement this interface.
    """
    
    @abstractmethod
    def load_model(self, model_id: str) -> bool:
        pass
        
    @abstractmethod
    def unload_model(self) -> bool:
        pass
        
    @abstractmethod
    def generate(self, context: Any, stream: bool = False) -> Any:
        pass
        
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        pass
        
    @abstractmethod
    def tokenize(self, text: str) -> list[int]:
        pass
        
    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def chat(self, model: str, messages: list, stream: bool = False, options: dict = None, **kwargs) -> Any:
        pass
