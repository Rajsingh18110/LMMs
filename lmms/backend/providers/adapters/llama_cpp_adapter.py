import os
import json
import asyncio
from typing import Dict, List, Any, AsyncGenerator, Optional
import httpx
from lmms.backend.contracts.provider import ProviderContract
from lmms.backend.contracts.runtime import ModelRuntime
from lmms.backend.contracts.generation import GenerationRequest, GenerationEvent

class LlamaCppRuntime(ModelRuntime):
    """
    Production-ready Llama.cpp runtime adapter.
    Executes inference via llama-cpp-python native bindings when local GGUF path is provided,
    or bridges seamlessly to the local LMMs high-speed engine endpoint (http://localhost:11435).
    """
    def __init__(self, model_path: str, engine_url: str = "http://localhost:11435"):
        self.model_path = model_path
        self.engine_url = engine_url.rstrip("/")
        self._cancel = False
        self._llm_instance = None
        
        # Lazy load llama_cpp if file exists
        if os.path.isfile(self.model_path):
            try:
                from llama_cpp import Llama
                self._llm_instance = Llama(
                    model_path=self.model_path,
                    n_ctx=4096,
                    verbose=False
                )
            except Exception:
                self._llm_instance = None

    async def generate(self, request: GenerationRequest) -> GenerationEvent:
        self._cancel = False
        prompt_text = request.prompt
        messages = request.messages or [{"role": "user", "content": prompt_text}]

        # 1. Native Llama instance execution
        if self._llm_instance is not None:
            loop = asyncio.get_running_loop()
            try:
                def _run_native():
                    return self._llm_instance.create_chat_completion(
                        messages=messages,
                        temperature=request.temperature if hasattr(request, "temperature") else 0.7,
                        max_tokens=request.max_tokens if hasattr(request, "max_tokens") else 2048,
                        stream=False
                    )
                resp = await loop.run_in_executor(None, _run_native)
                content = resp["choices"][0]["message"].get("content", "")
                return GenerationEvent(type="generation_completed", content=content, usage=resp.get("usage"))
            except Exception as e:
                # Fallback to HTTP engine
                pass

        # 2. Local LMMs Engine HTTP execution
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model_name": os.path.basename(self.model_path) if self.model_path else "default",
                "messages": messages,
                "stream": False,
                "temperature": getattr(request, "temperature", 0.7),
                "max_tokens": getattr(request, "max_tokens", 2048)
            }
            try:
                resp = await client.post(f"{self.engine_url}/v1/chat/completions", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = ""
                    if "message" in data:
                        content = data["message"].get("content", "")
                    elif "choices" in data and data["choices"]:
                        content = data["choices"][0].get("message", {}).get("content", "")
                    return GenerationEvent(type="generation_completed", content=content, usage=data.get("usage"))
                else:
                    return GenerationEvent(type="generation_error", content=f"Engine HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                return GenerationEvent(type="generation_error", content=f"Inference execution failed: {str(e)}")

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[GenerationEvent, None]:
        self._cancel = False
        yield GenerationEvent(type="generation_started")
        
        prompt_text = request.prompt
        messages = request.messages or [{"role": "user", "content": prompt_text}]

        # 1. Native Llama instance streaming
        if self._llm_instance is not None:
            loop = asyncio.get_running_loop()
            try:
                def _stream_native():
                    return self._llm_instance.create_chat_completion(
                        messages=messages,
                        temperature=getattr(request, "temperature", 0.7),
                        max_tokens=getattr(request, "max_tokens", 2048),
                        stream=True
                    )
                chunks_iter = await loop.run_in_executor(None, _stream_native)
                for chunk in chunks_iter:
                    if self._cancel:
                        yield GenerationEvent(type="generation_cancelled")
                        return
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield GenerationEvent(type="content_delta", content=delta)
                yield GenerationEvent(type="generation_completed")
                return
            except Exception:
                pass

        # 2. Local LMMs Engine SSE streaming
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model_name": os.path.basename(self.model_path) if self.model_path else "default",
                    "messages": messages,
                    "stream": True,
                    "temperature": getattr(request, "temperature", 0.7),
                    "max_tokens": getattr(request, "max_tokens", 2048)
                }
                async with client.stream("POST", f"{self.engine_url}/v1/chat/completions", json=payload) as response:
                    async for line in response.aiter_lines():
                        if self._cancel:
                            yield GenerationEvent(type="generation_cancelled")
                            return
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            delta_json = json.loads(data_str)
                            delta_text = ""
                            if "choices" in delta_json and delta_json["choices"]:
                                delta_text = delta_json["choices"][0].get("delta", {}).get("content", "")
                            elif "delta" in delta_json:
                                delta_text = delta_json["delta"]
                            if delta_text:
                                yield GenerationEvent(type="content_delta", content=delta_text)
                        except Exception:
                            continue
                yield GenerationEvent(type="generation_completed")
        except Exception as e:
            yield GenerationEvent(type="generation_error", content=f"Stream error: {str(e)}")

    async def estimate_tokens(self, request: GenerationRequest) -> int:
        text = request.prompt or ""
        if request.messages:
            text += "".join(str(m.get("content", "")) for m in request.messages)
        if self._llm_instance is not None:
            try:
                return len(self._llm_instance.tokenize(text.encode("utf-8")))
            except Exception:
                pass
        return max(1, len(text) // 3)

    def cancel(self) -> None:
        self._cancel = True

class LocalNativeProvider(ProviderContract):
    """
    Handles local GGUF models running natively on Llama.cpp
    """
    def __init__(self, provider_id: str, config: Dict[str, Any]):
        self.provider_id = provider_id
        self.config = config

    def test_connection(self) -> Dict[str, Any]:
        """Local native is always connected if llama_cpp is installed or engine is up."""
        try:
            import llama_cpp
            return {"success": True, "message": f"llama_cpp-python {llama_cpp.__version__} active"}
        except ImportError:
            # Check engine HTTP
            try:
                r = httpx.get("http://localhost:11435/v1/models", timeout=2.0)
                if r.status_code == 200:
                    return {"success": True, "message": "LMMs Engine HTTP active on port 11435"}
            except Exception:
                pass
            return {"success": False, "message": "llama-cpp-python not installed and engine port 11435 unreachable"}

    def scan_models(self) -> List[Dict[str, Any]]:
        models_dir = os.path.expanduser("~/.lmms/models")
        found = []
        if os.path.exists(models_dir):
            for root, _, files in os.walk(models_dir):
                for f in files:
                    if f.endswith(".gguf"):
                        fp = os.path.join(root, f)
                        found.append({
                            "id": f,
                            "name": f,
                            "path": fp,
                            "size_bytes": os.path.getsize(fp)
                        })
        return found

    def get_runtime(self) -> ModelRuntime:
        path = self.config.get("path", "")
        engine_url = self.config.get("engine_url", "http://localhost:11435")
        return LlamaCppRuntime(path, engine_url=engine_url)
