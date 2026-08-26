from typing import Dict, List, Any, AsyncGenerator
import json
import httpx
from lmms.backend.contracts.provider import ProviderContract
from lmms.backend.contracts.runtime import ModelRuntime
from lmms.backend.contracts.generation import GenerationRequest, GenerationEvent

class OpenAICompatibleRuntime(ModelRuntime):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self._cancel = False

    async def generate(self, request: GenerationRequest) -> GenerationEvent:
        # In full implementation, this will do the non-streaming REST call.
        # For Phase 1, we just return a skeleton event.
        return GenerationEvent(
            type="generation_completed",
            content="[Skeleton Response]",
            usage=None
        )

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[GenerationEvent, None]:
        # Skeleton for streaming response
        self._cancel = False
        yield GenerationEvent(type="generation_started")
        
        # Real implementation would make httpx stream request here
        # parsing `data: {...}` lines for content, reasoning, usage
        
        if self._cancel:
            yield GenerationEvent(type="generation_cancelled")
            return
            
        yield GenerationEvent(type="content_delta", content="[Skeleton Stream Content]")
        yield GenerationEvent(type="generation_completed")

    async def estimate_tokens(self, request: GenerationRequest) -> int:
        return 0

    def cancel(self) -> None:
        self._cancel = True

class OpenAICompatibleProvider(ProviderContract):
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key", "")

    def test_connection(self) -> Dict[str, Any]:
        """Verify network connectivity and auth."""
        url = f"{self.base_url.rstrip('/')}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            # Synchronous test for simplicity
            response = httpx.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("data", [])
                return {
                    "success": True, 
                    "message": "Connected successfully",
                    "available_models": [m.get("id") for m in models]
                }
            else:
                return {
                    "success": False, 
                    "message": f"Auth failed or endpoint error: {response.status_code} {response.text}"
                }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}

    def scan_models(self) -> List[Dict[str, Any]]:
        """Fetch models from the OpenAI /v1/models endpoint."""
        url = f"{self.base_url.rstrip('/')}/models"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            response = httpx.get(url, headers=headers, timeout=5.0)
            if response.status_code == 200:
                data = response.json().get("data", [])
                return [
                    {
                        "model_id": m.get("id"),
                        "display_name": m.get("id"),
                        "provider_id": self.provider_id,
                        # Assuming text defaults for unverified remote models
                        "modality": "text", 
                        "capabilities": {
                            "text": True,
                            "vision": False,
                            "streaming": True,
                            "tools": False, # Wait to be enabled manually or tested
                            "thinking": False
                        }
                    }
                    for m in data
                ]
        except Exception:
            pass
        return []

    def get_runtime(self) -> ModelRuntime:
        return OpenAICompatibleRuntime(self.base_url, self.api_key)
