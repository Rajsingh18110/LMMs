from typing import Protocol, Dict, List, Any

class ProviderContract(Protocol):
    """Protocol for external model sources (Ollama API, LM Studio API, HuggingFace)."""
    
    def scan_models(self) -> List[Dict[str, Any]]:
        """Returns a list of Model Manifests."""
        ...
        
    def fetch_model(self, model_id: str) -> bool:
        ...
