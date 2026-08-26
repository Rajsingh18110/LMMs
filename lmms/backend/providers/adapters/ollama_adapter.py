from typing import Dict, List, Any, AsyncGenerator
import json
import httpx
from lmms.backend.contracts.provider import ProviderContract
from lmms.backend.contracts.runtime import ModelRuntime
from lmms.backend.contracts.generation import GenerationRequest, GenerationEvent

class OllamaRuntime(ModelRuntime):
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self._cancel = False

    async def generate(self, request: GenerationRequest) -> GenerationEvent:
        return GenerationEvent(
            type="generation_completed",
            content="[Skeleton Ollama Response]",
            usage=None
        )

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[GenerationEvent, None]:
        self._cancel = False
        yield GenerationEvent(type="generation_started")
        
        # Real implementation would make httpx stream request here
        
        if self._cancel:
            yield GenerationEvent(type="generation_cancelled")
            return
            
        yield GenerationEvent(type="content_delta", content="[Skeleton Ollama Stream Content]")
        yield GenerationEvent(type="generation_completed")

    async def estimate_tokens(self, request: GenerationRequest) -> int:
        return 0

    def cancel(self) -> None:
        self._cancel = True

class OllamaProvider(ProviderContract):
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.base_url = config.get("base_url", "http://localhost:11434")

    def test_connection(self) -> Dict[str, Any]:
        """Verify network connectivity to Ollama."""
        url = f"{self.base_url}/api/tags"
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "success": True, 
                    "message": "Connected successfully to Ollama",
                    "available_models": [m.get("name") for m in models]
                }
            else:
                return {
                    "success": False, 
                    "message": f"Endpoint error: {response.status_code} {response.text}"
                }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def scan_models(self) -> List[Dict[str, Any]]:
        """Fetch models from the Ollama tags endpoint."""
        url = f"{self.base_url}/api/tags"
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json().get("models", [])
                return [
                    {
                        "model_id": m.get("name"),
                        "display_name": m.get("name"),
                        "provider_id": self.provider_id,
                        "modality": "text", 
                        "capabilities": {
                            "text": True,
                            "vision": "llava" in m.get("name", "").lower(),
                            "streaming": True,
                            "tools": True, 
                            "thinking": "deepseek-r1" in m.get("name", "").lower()
                        }
                    }
                    for m in data
                ]
        except Exception:
            pass
        return []

    def get_runtime(self) -> ModelRuntime:
        return OllamaRuntime(self.base_url)
