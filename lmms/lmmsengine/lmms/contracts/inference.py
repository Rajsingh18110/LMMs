from typing import Protocol, Any, Dict, Generator

class InferenceContract(Protocol):
    """Low-level protocol for inference execution."""
    
    def forward_pass(self, tokens: list[int]) -> list[float]:
        """Returns logits."""
        ...
        
    def sample(self, logits: list[float], params: Dict[str, Any]) -> int:
        """Returns sampled token."""
        ...
