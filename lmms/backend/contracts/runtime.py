from typing import Protocol, Any, Dict

class RuntimeContract(Protocol):
    """Protocol for LMMs engines (Ollama, llama.cpp, AirLLM, vLLM)."""
    
    def load_model(self, model_id: str, manifest: Dict[str, Any]) -> bool:
        ...
        
    def unload_model(self, model_id: str) -> bool:
        ...
        
    def generate(self, prompt: str, **kwargs) -> str:
        ...
        
    def stream(self, prompt: str, **kwargs) -> Any:
        ...
        
    def embeddings(self, text: str) -> list[float]:
        ...
        
    def health(self) -> Dict[str, Any]:
        """Returns runtime status, VRAM usage, etc."""
        ...
