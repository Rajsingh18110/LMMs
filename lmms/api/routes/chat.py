import os
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from lmms.engine.manager import engine_manager

router = APIRouter(prefix="/v1/chat", tags=["chat"])

MODELS_DIR = os.path.expanduser("~/.lmms/models")


class ChatRequest(BaseModel):
    model_name: Optional[str] = None
    model: Optional[str] = None
    messages: List[Dict[str, Any]]
    stream: bool = True
    mode: Optional[str] = "deep"
    think: Optional[bool] = True


def fuzzy_match_model(req_name: str, loaded_keys: List[str]) -> Optional[str]:
    """Return the actual key in loaded_keys that best matches req_name, or None."""
    if req_name in loaded_keys:
        return req_name

    def norm(s: str) -> str:
        return s.lower().replace(".gguf", "").replace("-", "").replace("_", "").replace(":", "").replace(".", "").replace(" ", "")

    req_norm = norm(req_name)
    for key in loaded_keys:
        if norm(key) == req_norm:
            return key
        if req_norm in norm(key) or norm(key) in req_norm:
            return key
    return None


@router.post("/completions")
async def chat_completions(req: ChatRequest):
    req_name = req.model_name or req.model or ""
    if not req_name:
        loaded = engine_manager.get_loaded_models()
        if loaded:
            req_name = list(loaded.keys())[0]
        else:
            raise HTTPException(status_code=400, detail="Missing 'model_name' or 'model' in request.")
    req.model_name = req_name

    runtime = None
    loaded_models = engine_manager.get_loaded_models()

    matched_key = fuzzy_match_model(req.model_name, list(loaded_models.keys()))
    if matched_key:
        req.model_name = matched_key
        runtime = engine_manager.get_runtime(matched_key)
    elif getattr(engine_manager.pytorch_runtime, "_is_loaded", False) and getattr(engine_manager.pytorch_runtime, "_model_id", "") == req.model_name:
        runtime = engine_manager.pytorch_runtime

    # Auto-load logic if runtime not currently loaded
    if not runtime:
        path = os.path.join(MODELS_DIR, f"{req.model_name}.gguf")

        if not os.path.exists(path):
            try:
                downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                if os.path.exists(downloads_file):
                    with open(downloads_file, "r") as f:
                        d = json.load(f)
                    if req.model_name in d and d[req.model_name].get("file"):
                        path = os.path.join(MODELS_DIR, d[req.model_name]["file"])
            except Exception:
                pass

        if not os.path.exists(path):
            search_term = req.model_name.replace(":", "-").lower()
            if os.path.exists(MODELS_DIR):
                for f in os.listdir(MODELS_DIR):
                    if f.endswith(".gguf") and search_term in f.lower():
                        path = os.path.join(MODELS_DIR, f)
                        break

        if os.path.exists(path):
            # Engine 1: Air + Llama.cpp GGUF
            size_gb = os.path.getsize(path) / (1024**3)
            if engine_manager.cache.can_fit(size_gb):
                engine_manager.cache.load_model(req.model_name, size_gb)
                runtime = engine_manager.engine_1
                success = runtime.load_model(path)
                if not success:
                    engine_manager.cache.unload_model(req.model_name)
                    raise HTTPException(status_code=500, detail="Failed to load model into Engine 1.")
            else:
                raise HTTPException(status_code=507, detail="Insufficient memory to auto-load model.")
        else:
            # Fallback to Engine 2: PyTorch Runtime
            runtime = engine_manager.engine_2
            success = runtime.load_model(req.model_name)
            if not success:
                raise HTTPException(status_code=404, detail=f"Model '{req.model_name}' could not be loaded into Engine 1 or Engine 2.")

    context = {
        "messages": req.messages,
        "model": req.model_name,
        "model_name": req.model_name,
        "mode": req.mode,
        "think": req.think
    }

    if req.stream:
        async def event_generator():
            try:
                generator = runtime.generate(context, stream=True)
                for chunk in generator:
                    msg = chunk.get("message", chunk)
                    yield f"data: {json.dumps(msg)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        response = runtime.generate(context, stream=False)
        return response
