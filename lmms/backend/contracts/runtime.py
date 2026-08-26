from typing import Protocol, Any, Dict, AsyncGenerator
from lmms.backend.contracts.generation import GenerationRequest, GenerationEvent

class ModelRuntime(Protocol):
    """Protocol for all model inference executions (Local and External)."""
    
    async def generate(self, request: GenerationRequest) -> GenerationEvent:
        """Single generation resulting in a final event."""
        ...
        
    async def stream(self, request: GenerationRequest) -> AsyncGenerator[GenerationEvent, None]:
        """Streaming generation yielding intermediate events."""
        ...
        
    async def estimate_tokens(self, request: GenerationRequest) -> int:
        """Estimate token count for a request prior to execution."""
        ...
        
    def cancel(self) -> None:
        """Cancel an ongoing generation request."""
        ...

