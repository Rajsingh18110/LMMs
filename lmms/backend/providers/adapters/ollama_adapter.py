from typing import Dict, List, Any, AsyncGenerator, Optional
import json
import httpx
from lmms.backend.contracts.provider import ProviderContract
from lmms.backend.contracts.runtime import ModelRuntime
from lmms.backend.contracts.generation import GenerationRequest, GenerationEvent

class OllamaRuntime(ModelRuntime):
    """
    Production-grade Ollama runtime adapter.
    Communicates directly with Ollama daemon via async HTTP streaming.
    """
    def __init__(self, base_url: str, default_model: str = "llama3"):
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self._cancel = False

    async def generate(self, request: GenerationRequest) -> GenerationEvent:
        self._cancel = False
        messages = request.messages or [{"role": "user", "content": request.prompt}]
        model = getattr(request, "model_name", None) or self.default_model
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": getattr(request, "temperature", 0.7),
                }
            }
            try:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    return GenerationEvent(type="generation_completed", content=content, usage=None)
                else:
                    return GenerationEvent(type="generation_error", content=f"Ollama error {resp.status_code}: {resp.text}")
            except Exception as e:
                return GenerationEvent(type="generation_error", content=f"Ollama execution error: {str(e)}")

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[GenerationEvent, None]:
        self._cancel = False
        yield GenerationEvent(type="generation_started")
        
        messages = request.messages or [{"role": "user", "content": request.prompt}]
        model = getattr(request, "model_name", None) or self.default_model

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": getattr(request, "temperature", 0.7),
                    }
                }
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                    async for line in response.aiter_lines():
                        if self._cancel:
                            yield GenerationEvent(type="generation_cancelled")
                            return
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            delta = chunk_data.get("message", {}).get("content", "")
                            if delta:
                                yield GenerationEvent(type="content_delta", content=delta)
                            if chunk_data.get("done", False):
                                break
                        except Exception:
                            continue
            yield GenerationEvent(type="generation_completed")
        except Exception as e:
            yield GenerationEvent(type="generation_error", content=f"Ollama stream error: {str(e)}")

    async def estimate_tokens(self, request: GenerationRequest) -> int:
        text = request.prompt or ""
        if request.messages:
            text += "".join(str(m.get("content", "")) for m in request.messages)
        return max(1, len(text) // 3)

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
        url = f"{self.base_url}/api/tags"
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [{
                    "id": m.get("name"),
                    "name": m.get("name"),
                    "size_bytes": m.get("size", 0),
                    "modified_at": m.get("modified_at")
                } for m in models]
        except Exception:
            pass
        return []

    def get_runtime(self) -> ModelRuntime:
        default_model = self.config.get("model", "llama3")
        return OllamaRuntime(self.base_url, default_model=default_model)
