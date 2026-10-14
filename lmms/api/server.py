import os
import json
import threading
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import asyncio
try:
    from huggingface_hub import hf_hub_download
except ImportError:
    hf_hub_download = None

from lmms.engine.manager import engine_manager

app = FastAPI(title="LMMs Engine API")

import time
import signal
import threading
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

LAST_PING_TIME = time.time()
ACTIVE_REQUESTS = 0
REQUEST_LOCK = threading.Lock()

class ActiveRequestsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        global ACTIVE_REQUESTS
        with REQUEST_LOCK:
            ACTIVE_REQUESTS += 1
            
        try:
            response = await call_next(request)
            if isinstance(response, StreamingResponse):
                original_body = response.body_iterator
                async def wrapped_body():
                    try:
                        async for chunk in original_body:
                            yield chunk
                    finally:
                        global ACTIVE_REQUESTS
                        with REQUEST_LOCK:
                            ACTIVE_REQUESTS -= 1
                response.body_iterator = wrapped_body()
                return response
            else:
                with REQUEST_LOCK:
                    ACTIVE_REQUESTS -= 1
                return response
        except Exception:
            with REQUEST_LOCK:
                ACTIVE_REQUESTS -= 1
            raise

app.add_middleware(ActiveRequestsMiddleware)

@app.post("/v1/internal/ping")
def ping():
    global LAST_PING_TIME
    LAST_PING_TIME = time.time()
    return {"status": "ok"}

@app.post("/v1/internal/shutdown")
def shutdown():
    import os
    print("[Engine] Immediate shutdown requested by client.")
    os._exit(0)
    return {"status": "shutting down"}

async def heartbeat_monitor():
    while True:
        await asyncio.sleep(5)
        # If no ping in 30 seconds, and no active requests, exit gracefully
        with REQUEST_LOCK:
            active_count = ACTIVE_REQUESTS
            
        if active_count == 0 and (time.time() - LAST_PING_TIME > 30):
            print("[Engine] No active clients. Shutting down gracefully to save memory.")
            import os
            os._exit(0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(heartbeat_monitor())


# Ensure models directory exists
MODELS_DIR = os.path.expanduser("~/.lmms/models")
os.makedirs(MODELS_DIR, exist_ok=True)

class LoadRequest(BaseModel):
    model_name: str
    model_path: Optional[str] = None

class UnloadRequest(BaseModel):
    model_name: str

class PullRequest(BaseModel):
    model_name: str
    file_name: Optional[str] = None

class ChatRequest(BaseModel):
    model_name: str
    messages: List[Dict[str, Any]]
    stream: bool = True
    mode: Optional[str] = "deep"
    think: Optional[bool] = True
    temperature: Optional[float] = 0.8
    top_p: Optional[float] = 0.95
    repetition_penalty: Optional[float] = 1.15

class DoctorRequest(BaseModel):
    fix: bool = False

class TokenizeRequest(BaseModel):
    model_name: str
    texts: List[str]

@app.post("/v1/models/load")
async def load_model(req: LoadRequest):
    path = req.model_path or os.path.join(MODELS_DIR, f"{req.model_name}.gguf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Model file not found")

    # Check if already loaded
    key = os.path.basename(path).replace(".gguf", "")
    if key in engine_manager.runtime._models:
        return {"status": "success", "stats": engine_manager.cache.get_stats()}

    # Unload all previous models to prevent OOM
    for loaded_model in list(engine_manager.cache.loaded_models.keys()):
        engine_manager.cache.unload_model(loaded_model)
    engine_manager.runtime.unload_model()

    size_gb = os.path.getsize(path) / (1024**3)

    if not engine_manager.cache.can_fit(size_gb):
        raise HTTPException(status_code=507, detail="Insufficient VRAM/RAM to load model")

    # Register in cache
    engine_manager.cache.load_model(req.model_name, size_gb)

    # Actually load into runtime (llama_cpp)
    success = await asyncio.to_thread(engine_manager.runtime.load_model, path)
    if not success:
        engine_manager.cache.unload_model(req.model_name)
        raise HTTPException(status_code=500, detail="Failed to initialize runtime")

    return {"status": "success", "stats": engine_manager.cache.get_stats()}

@app.post("/v1/models/unload")
def unload_model(req: UnloadRequest):
    engine_manager.runtime.unload_model()
    engine_manager.cache.unload_model(req.model_name)
    engine_manager.air_scheduler.remove_model(req.model_name)
    return {"status": "success", "message": f"Model {req.model_name} unloaded."}

@app.get("/v1/air/ps")
def air_ps():
    return engine_manager.air_scheduler.get_ps()

@app.get("/v1/air/stats")
def air_stats():
    from lmms.engine.air.stats import AirStats
    return AirStats.get_system_stats()

@app.get("/v1/air/cache")
def air_cache():
    import os
    from lmms.engine.registry import RegistryManager
    reg = RegistryManager()
    
    # Get all downloaded models
    disk_models = []
    if os.path.exists(reg.models_dir):
        for f in os.listdir(reg.models_dir):
            if f.endswith(".gguf"):
                disk_models.append(f.replace(".gguf", ""))
                
    vram_models = [m["model"] for m in engine_manager.air_scheduler.get_ps() if m["vram_gb"] > 0]
    ram_models = engine_manager.air_ram_cache.get_models()
    
    return {
        "vram_models": vram_models,
        "ram_models": ram_models,
        "disk_models": [m for m in disk_models if m not in vram_models and m not in ram_models]
    }

@app.post("/v1/air/generate")
async def air_generate(req: ChatRequest):
    model_name = req.model_name
    
    # We don't forcefully evict everything anymore.
    # The Swapper will automatically handle eviction if VRAM is constrained.
    
    # We must resolve the path to load the model physically
    import os, json
    from lmms.engine.registry import RegistryManager
    reg = RegistryManager()
    path = os.path.join(reg.models_dir, f"{model_name}.gguf")
    
    if not os.path.exists(path):
        # Try to resolve via downloads.json mapping
        try:
            downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
            if os.path.exists(downloads_file):
                with open(downloads_file, "r") as f: d = json.load(f)
                if model_name in d and d[model_name].get("file"):
                    path = os.path.join(reg.models_dir, d[model_name]["file"])
        except Exception: pass

    if not os.path.exists(path):
        # Fallback to fuzzy search
        search_term = model_name.replace(":", "-").lower()
        for f in os.listdir(reg.models_dir):
            if f.endswith(".gguf") and search_term in f.lower():
                path = os.path.join(reg.models_dir, f)
                break

    if not os.path.exists(path):
        manifest_path = os.path.join(reg.manifests_dir, f"{model_name}.json")
        if os.path.exists(manifest_path):
            import json
            with open(manifest_path, "r") as f:
                data = json.load(f)
                base = data.get("base_model", "")
                path = os.path.join(reg.models_dir, f"{base}.gguf") if not base.endswith(".gguf") else os.path.join(reg.models_dir, base)
                
    if os.path.exists(path):
        size_gb = os.path.getsize(path) / (1024**3)
        # Ensure we have VRAM capacity before loading
        if not engine_manager.air_swapper.ensure_vram_capacity(size_gb):
            raise Exception("Insufficient VRAM to load this model, even after eviction.")
            
        # Physically load it
        success = await asyncio.to_thread(engine_manager.runtime.load_model, path)
        if not success:
            raise HTTPException(status_code=500, detail="Engine failed to load model into VRAM (Possible OOM or driver issue).")
        
        # Logically update the swapper
        if model_name in engine_manager.air_scheduler.active_models:
            if engine_manager.air_scheduler.active_models[model_name]["location"] != "VRAM":
                engine_manager.air_swapper.swap_to_vram(model_name)
        else:
            engine_manager.air_scheduler.register_model(model_name, "VRAM", size_gb, 0.0)
    engine_manager.air_scheduler.update_state(model_name, "Generating")
    
    def stream_air():
        import json
        try:
            for chunk in engine_manager.runtime.generate({"messages": req.messages}, stream=True):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            engine_manager.air_scheduler.update_state(model_name, "Keep Warm")
            
    return StreamingResponse(stream_air(), media_type="text/plain")

@app.get("/v1/models/list")
async def list_models():
    models = []
    for file in os.listdir(MODELS_DIR):
        if file.endswith(".gguf"):
            path = os.path.join(MODELS_DIR, file)
            size_gb = os.path.getsize(path) / (1024**3)
            models.append({
                "name": file.replace(".gguf", ""),
                "size_gb": round(size_gb, 2)
            })
    return {"models": models}

@app.get("/v1/models/ps")
async def ps_models():
    return engine_manager.cache.get_stats()

@app.get("/v1/models/info/{model_name}")
async def info_model(model_name: str):
    path = os.path.join(MODELS_DIR, f"{model_name}.gguf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    size_gb = os.path.getsize(path) / (1024**3)
    mod_time = os.path.getmtime(path)
    
    # Try to guess quantization from filename
    quant = "unknown"
    lower_name = model_name.lower()
    for q in ["q4_k_m", "q8_0", "f16", "q5_k_m", "q2_k"]:
        if q in lower_name:
            quant = q
            break
            
    return {
        "name": model_name,
        "path": path,
        "size_gb": round(size_gb, 2),
        "modified_timestamp": mod_time,
        "quantization": quant,
        "architecture": "llama" # Mocked for now
    }

@app.get("/v1/benchmark")
async def run_benchmark():
    try:
        from lmms.engine.benchmark import BenchmarkEngine
        # Mock 6GB VRAM for now
        results = BenchmarkEngine().run_benchmarks({"vram_total_mb": 6000})
        return {"status": "success", "benchmarks": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/models/delete/{model_name}")
async def delete_model(model_name: str):
    path = os.path.join(MODELS_DIR, f"{model_name}.gguf")
    if model_name in engine_manager.runtime._models or (model_name + ".gguf") in engine_manager.runtime._models:
        engine_manager.cache.unload_model(model_name)
        await asyncio.to_thread(engine_manager.runtime.unload_model, model_name)
    if os.path.exists(path):
        os.remove(path)
        return {"status": "success", "message": f"Deleted {model_name}"}
    raise HTTPException(status_code=404, detail="Model file not found")

@app.get("/v1/models/search")
async def search_models(q: str):
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        models = api.list_models(search=q, filter="gguf", limit=10)
        results = []
        for m in models:
            results.append({
                "modelId": m.id,
                "author": m.author or "Unknown",
                "downloads": getattr(m, "downloads", 0),
                "last_updated": str(getattr(m, "lastModified", "Unknown")),
                "gguf_available": True
            })
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/doctor")
async def engine_doctor(req: DoctorRequest):
    import sys
    import shutil
    
    report = {
        "engine_reachable": True,
        "models_dir_exists": os.path.exists(MODELS_DIR),
        "models_dir_writable": os.access(MODELS_DIR, os.W_OK) if os.path.exists(MODELS_DIR) else False,
        "python_version": sys.version.split(" ")[0],
        "cuda_support": False,
        "llama_cpp_python": False,
        "ram_available_gb": 0.0,
        "disk_available_gb": 0.0
    }
    
    try:
        import psutil
        report["ram_available_gb"] = round(psutil.virtual_memory().available / (1024**3), 2)
    except:
        pass
        
    if os.path.exists(MODELS_DIR):
        total, used, free = shutil.disk_usage(MODELS_DIR)
        report["disk_available_gb"] = round(free / (1024**3), 2)
        
    try:
        import llama_cpp
        report["llama_cpp_python"] = True
        import torch
        report["cuda_support"] = torch.cuda.is_available()
    except:
        pass
        
    fixes_applied = []
    if req.fix:
        if not report["models_dir_exists"]:
            os.makedirs(MODELS_DIR, exist_ok=True)
            report["models_dir_exists"] = True
            report["models_dir_writable"] = True
            fixes_applied.append("Created ~/.lmms/models/")
        
        if not report["cuda_support"]:
            fixes_applied.append("SUGGESTION: Run `CMAKE_ARGS='-DGGML_CUDA=on' pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir`")
            
        engine_manager.runtime.unload_model()
        fixes_applied.append("Cleared VRAM cache and unloaded models.")
        
    return {"report": report, "fixes": fixes_applied}

def download_model_task(model_name: str, file_name: Optional[str] = None):
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        if "/" in model_name:
            repo_id = model_name
        else:
            # Map ollama tags to HF search
            search_term = model_name.replace(":", "-").lower()
            KNOWN_MODELS = {
                "qwen3-8b": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                "qwen3": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                "gemma": "bartowski/gemma-2-9b-it-GGUF",
                "llama3": "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF",
                "llama3-8b": "QuantFactory/Meta-Llama-3-8B-Instruct-GGUF"
            }
            if search_term in KNOWN_MODELS:
                repo_id = KNOWN_MODELS[search_term]
            else:
                models = list(api.list_models(search=search_term, filter="gguf", limit=1))
                if models:
                    repo_id = models[0].id
                else:
                    downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                    try:
                        with open(downloads_file, "r") as f: state = json.load(f)
                        state[model_name] = {"status": "failed (not found)", "repo": model_name, "file": ""}
                        with open(downloads_file, "w") as f: json.dump(state, f)
                    except Exception: pass
                    print(f"Could not find any GGUF repo matching {model_name}")
                    return
                
        if file_name:
            target_file = file_name
        else:
            files = api.list_repo_files(repo_id=repo_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]
            if not gguf_files:
                print(f"No GGUF files found in {repo_id}")
                return
                
            target_file = gguf_files[0]
            for f in gguf_files:
                if "q4_k_m" in f.lower():
                    target_file = f
                    break
                
        print(f"Starting download for {repo_id}/{target_file}...")
        
        # Track active download
        downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
        os.makedirs(os.path.dirname(downloads_file), exist_ok=True)
        state = {}
        if os.path.exists(downloads_file):
            try:
                with open(downloads_file, "r") as f:
                    state = json.load(f)
            except Exception: pass
            
        state[model_name] = {"status": "0%", "repo": repo_id, "file": target_file}
        with open(downloads_file, "w") as f:
            json.dump(state, f)
            
        # Force HF logging to INFO to ensure tqdm is not disabled
        import logging
        logging.getLogger("huggingface_hub").setLevel(logging.INFO)

        from huggingface_hub.utils import _tqdm
        original_tqdm = _tqdm.tqdm

        # Use a global dictionary to track the maximum total size seen
        # because HF hub creates multiple tqdm instances for one file
        progress_state = {"total": 0, "n": 0}

        class DownloadTqdm(original_tqdm):
            def update(self, n=1):
                super().update(n)
                if hasattr(self, 'total') and self.total:
                    progress_state["total"] = max(progress_state["total"], self.total)
                
                # If this is a progress bar that is advancing, update n
                if self.n > 0:
                    progress_state["n"] = max(progress_state["n"], self.n)
                
                total = progress_state["total"]
                current = progress_state["n"]
                
                if total > 0:
                    pct = int((current / total) * 100)
                    size_str = f"{current / 1024 / 1024 / 1024:.2f}G/{total / 1024 / 1024 / 1024:.2f}G"
                else:
                    pct = 0
                    size_str = f"{current / 1024 / 1024:.2f}M/???"
                
                speed = getattr(self, 'format_dict', {}).get('rate', 0)
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else ""
                
                try:
                    with open(downloads_file, "r") as file: d = json.load(file)
                    if d.get(model_name, {}).get("cancel", False):
                        raise RuntimeError("Download cancelled by user.")
                        
                    d[model_name]["status"] = f"{pct}% ({size_str} @ {speed_str})"
                    with open(downloads_file, "w") as file: json.dump(d, file)
                except RuntimeError as re:
                    raise re
                except Exception: pass

        _tqdm.tqdm = DownloadTqdm
        
        try:
            if hf_hub_download is None:
                raise ImportError("huggingface_hub is not installed. Please install it with: pip install huggingface_hub")
            hf_hub_download(repo_id=repo_id, filename=target_file, local_dir=MODELS_DIR)
            
            # Set state to complete
            try:
                with open(downloads_file, "r") as f: state = json.load(f)
                state[model_name]["status"] = "complete"
                with open(downloads_file, "w") as f: json.dump(state, f)
            except Exception: pass
            
        finally:
            _tqdm.tqdm = original_tqdm # Restore original just in case
            
        print("Download complete.")
    except Exception as e:
        downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
        try:
            with open(downloads_file, "r") as f: state = json.load(f)
            state[model_name] = {"status": "failed", "error": str(e)}
            with open(downloads_file, "w") as f: json.dump(state, f)
        except Exception: pass
        print(f"Download failed: {e}")

@app.post("/v1/models/pull")
async def pull_model(req: PullRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(download_model_task, req.model_name, req.file_name)
    return {"status": "downloading", "model": req.model_name, "file": req.file_name}

@app.get("/v1/model/context")
async def get_model_context(model_name: str):
    def norm(s):
        return s.lower().replace(".gguf", "").replace("-", "").replace("_", "").replace(":", "").replace(".", "").replace(" ", "")
    req_norm = norm(model_name)
    matched_key = None
    for key in engine_manager.runtime._models.keys():
        if norm(key) == req_norm or req_norm in norm(key) or norm(key) in req_norm:
            matched_key = key
            break
    
    if matched_key and matched_key in engine_manager.runtime._models:
        active_model = engine_manager.runtime._models[matched_key]
        n_ctx = active_model.n_ctx()
        return {
            "status": "success",
            "context_length": n_ctx,
            "max_response_tokens": int(n_ctx * 0.18) if n_ctx > 0 else 1024
        }
    return {"status": "error", "detail": "Model not loaded in text runtime"}

@app.post("/v1/tokenize")
async def tokenize_text(req: TokenizeRequest):
    try:
        def batch_tokenize():
            counts = []
            for t in req.texts:
                tokens = engine_manager.runtime.tokenize(t)
                counts.append(len(tokens))
            return counts
            
        counts = await asyncio.to_thread(batch_tokenize)
        return {"status": "success", "token_counts": counts}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    # Ensure a model is loaded. If not, auto-load?
    runtime = None
    
    def _fuzzy_match_model(req_name: str, loaded_keys) -> str | None:
        """Return the actual key in loaded_keys that best matches req_name, or None."""
        # Exact match first
        if req_name in loaded_keys:
            return req_name
        # Normalize: lowercase, strip .gguf, replace - and : with spaces
        def norm(s):
            return s.lower().replace(".gguf", "").replace("-", "").replace("_", "").replace(":", "").replace(".", "").replace(" ", "")
        req_norm = norm(req_name)
        for key in loaded_keys:
            if norm(key) == req_norm:
                return key
            # Partial match: req_name normalized is substring of key normalized
            if req_norm in norm(key) or norm(key) in req_norm:
                return key
        return None

    # Check if loaded in llama runtime
    matched_key = _fuzzy_match_model(req.model_name, list(engine_manager.runtime._models.keys()))
    if matched_key:
        # Normalize the request model_name to the actual loaded key
        req.model_name = matched_key
        runtime = engine_manager.runtime
    # Check if loaded in pytorch runtime
    elif getattr(engine_manager.pytorch_runtime, "_is_loaded", False) and getattr(engine_manager.pytorch_runtime, "_model_id", "") == req.model_name:
        runtime = engine_manager.pytorch_runtime
    
    # Auto-load logic
    if not runtime:
        path = os.path.join(MODELS_DIR, f"{req.model_name}.gguf")
        
        if not os.path.exists(path):
            try:
                downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                if os.path.exists(downloads_file):
                    with open(downloads_file, "r") as f: d = json.load(f)
                    if req.model_name in d and d[req.model_name].get("file"):
                        path = os.path.join(MODELS_DIR, d[req.model_name]["file"])
            except Exception: pass

        if not os.path.exists(path):
            search_term = req.model_name.replace(":", "-").lower()
            for f in os.listdir(MODELS_DIR):
                if f.endswith(".gguf") and search_term in f.lower():
                    path = os.path.join(MODELS_DIR, f)
                    break

        if os.path.exists(path):
            # It's a GGUF model -> LlamaCppRuntime
            size_gb = os.path.getsize(path) / (1024**3)
            if engine_manager.cache.can_fit(size_gb):
                engine_manager.cache.load_model(req.model_name, size_gb)
                success = await asyncio.to_thread(engine_manager.runtime.load_model, path)
                if not success:
                    engine_manager.cache.unload_model(req.model_name)
                    raise HTTPException(status_code=500, detail="Failed to load model. Is llama-cpp-python installed?")
                runtime = engine_manager.runtime
            else:
                raise HTTPException(status_code=507, detail="Insufficient memory to auto-load")
        else:
            # Fallback to PyTorch Runtime
            success = await asyncio.to_thread(engine_manager.pytorch_runtime.load_model, req.model_name)
            if success:
                runtime = engine_manager.pytorch_runtime
            else:
                raise HTTPException(status_code=404, detail=f"Model '{req.model_name}' not loaded and failed to initialize fallback PyTorch runtime.")
            
    if req.stream:
        async def event_generator():
            q = asyncio.Queue()
            loop = asyncio.get_running_loop()
            
            def producer():
                try:
                    generator = runtime.generate(
                        {"messages": req.messages, "mode": req.mode, "think": req.think, "model_name": req.model_name, "temperature": req.temperature, "top_p": req.top_p, "repetition_penalty": req.repetition_penalty}, 
                        stream=True
                    )
                    for chunk in generator:
                        loop.call_soon_threadsafe(q.put_nowait, chunk)
                except Exception as e:
                    loop.call_soon_threadsafe(q.put_nowait, e)
                finally:
                    loop.call_soon_threadsafe(q.put_nowait, None)

            import threading
            threading.Thread(target=producer, daemon=True).start()
            
            while True:
                item = await q.get()
                if item is None:
                    yield "data: [DONE]\n\n"
                    break
                if isinstance(item, Exception):
                    yield f"data: {json.dumps({'error': str(item)})}\n\n"
                    break
                yield f"data: {json.dumps(item['message'])}\n\n"
                
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        # Run synchronous generate in a thread to avoid blocking the event loop
        response = await asyncio.to_thread(
            runtime.generate, 
            {"messages": req.messages, "mode": req.mode, "think": req.think, "model_name": req.model_name, "temperature": req.temperature, "top_p": req.top_p, "repetition_penalty": req.repetition_penalty}, 
            stream=False
        )
        return response

import random
import string
from fastapi.responses import HTMLResponse

# Global Security State
server_otp = ""
server_api_key = ""
server_temp_token = ""
active_agent_name = "No Model Loaded"

@app.get("/v1/health")
async def health_check():
    return {"status": "ok"}

@app.get("/webhook")
async def webhook_get():
    # Like /v1/models/ps
    try:
        active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
        if os.path.exists(active_f):
            with open(active_f, "r") as f: d = json.load(f)
            return {"active_models": list(d.keys()), "engine": "running"}
    except Exception:
        pass
    return {"active_models": list(engine_manager.runtime._models.keys()), "engine": "running"}

@app.post("/webhook")
async def webhook_post(req: ChatRequest):
    # Pass directly to chat_completions
    return await chat_completions(req)

class UnlockRequest(BaseModel):
    otp: str

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LMMs Engine Dashboard | Powered by MarkanM</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --bg-primary: #07090e;
                --card-bg: rgba(14, 18, 27, 0.78);
                --card-border: rgba(255, 255, 255, 0.08);
                --accent-emerald: #10b981;
                --accent-cyan: #06b6d4;
                --accent-violet: #8b5cf6;
                --accent-amber: #f59e0b;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --glow-color: rgba(6, 182, 212, 0.12);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
                font-family: 'Inter', -apple-system, sans-serif; 
                background-color: var(--bg-primary);
                background-image: 
                    radial-gradient(circle at 15% 15%, rgba(16, 185, 129, 0.09) 0%, transparent 45%),
                    radial-gradient(circle at 85% 85%, rgba(139, 92, 246, 0.09) 0%, transparent 45%),
                    radial-gradient(circle at 50% 50%, rgba(6, 182, 212, 0.05) 0%, transparent 60%);
                color: var(--text-main); 
                min-height: 100vh;
                display: flex; 
                justify-content: center; 
                align-items: center; 
                padding: 30px 20px;
                overflow-x: hidden;
            }
            .ambient-mesh {
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background: linear-gradient(to right, rgba(255,255,255,0.01) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(255,255,255,0.01) 1px, transparent 1px);
                background-size: 40px 40px;
                pointer-events: none;
                z-index: 0;
            }
            .container {
                position: relative;
                z-index: 1;
                width: 100%;
                max-width: 680px;
            }
            .card { 
                background: var(--card-bg); 
                backdrop-filter: blur(28px);
                -webkit-backdrop-filter: blur(28px);
                border: 1px solid var(--card-border); 
                border-radius: 20px; 
                padding: 32px; 
                box-shadow: 0 24px 60px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.08); 
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .header-bar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 24px;
                padding-bottom: 20px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
            .brand-group {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .logo-icon {
                width: 42px;
                height: 42px;
                border-radius: 12px;
                background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 900;
                font-size: 20px;
                color: #041019;
                box-shadow: 0 0 20px rgba(16, 185, 129, 0.35);
            }
            .brand-title {
                font-size: 22px;
                font-weight: 800;
                letter-spacing: -0.5px;
                background: linear-gradient(90deg, #ffffff 30%, #a7f3d0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .brand-sub {
                font-size: 11px;
                color: var(--text-muted);
                letter-spacing: 0.5px;
                text-transform: uppercase;
                font-weight: 600;
            }
            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                border-radius: 9999px;
                background: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.25);
                font-size: 11px;
                font-weight: 600;
                color: #34d399;
            }
            .pulse-dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #10b981;
                box-shadow: 0 0 10px #10b981;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(0.95); opacity: 0.8; }
                50% { transform: scale(1.3); opacity: 1; }
                100% { transform: scale(0.95); opacity: 0.8; }
            }
            .model-banner {
                background: linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
                border: 1px solid rgba(6, 182, 212, 0.2);
                border-radius: 14px;
                padding: 16px 20px;
                margin-bottom: 24px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .model-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .model-label {
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                font-weight: 700;
                color: var(--accent-cyan);
            }
            .model-name {
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
            }
            .engine-tag {
                font-size: 11px;
                padding: 3px 8px;
                border-radius: 6px;
                background: rgba(245, 158, 11, 0.15);
                border: 1px solid rgba(245, 158, 11, 0.3);
                color: #fbbf24;
                font-weight: 600;
            }
            .layer-bar-wrap {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .layer-bar-info {
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: var(--text-muted);
            }
            .split-bar {
                height: 8px;
                border-radius: 4px;
                overflow: hidden;
                display: flex;
                background: rgba(255, 255, 255, 0.06);
            }
            .split-gpu {
                background: linear-gradient(90deg, #10b981, #06b6d4);
                height: 100%;
                transition: width 0.8s ease;
            }
            .split-cpu {
                background: linear-gradient(90deg, #8b5cf6, #ec4899);
                height: 100%;
                transition: width 0.8s ease;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 14px;
                margin-bottom: 24px;
            }
            .stat-box {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 14px;
            }
            .stat-title {
                font-size: 11px;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.6px;
                margin-bottom: 6px;
            }
            .stat-val {
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
                display: flex;
                align-items: baseline;
                gap: 6px;
            }
            .stat-sub {
                font-size: 11px;
                color: var(--text-muted);
                font-weight: 500;
            }
            .meter-bar {
                margin-top: 8px;
                height: 5px;
                border-radius: 3px;
                background: rgba(255, 255, 255, 0.06);
                overflow: hidden;
            }
            .meter-fill {
                height: 100%;
                background: var(--accent-emerald);
                transition: width 0.6s ease;
            }
            .meter-fill.violet {
                background: var(--accent-violet);
            }
            .field-group {
                margin-bottom: 20px;
            }
            .field-label {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                color: var(--text-muted);
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.6px;
                margin-bottom: 8px;
            }
            .field-badge {
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.08);
                color: #cbd5e1;
            }
            .input-box {
                position: relative;
                display: flex;
                align-items: center;
                background: rgba(3, 7, 18, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 4px 6px 4px 14px;
                transition: border-color 0.2s, box-shadow 0.2s;
            }
            .input-box:focus-within {
                border-color: var(--accent-cyan);
                box-shadow: 0 0 15px rgba(6, 182, 212, 0.25);
            }
            .code-text {
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                color: #38bdf8;
                width: 100%;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                user-select: all;
            }
            .action-btn-group {
                display: flex;
                align-items: center;
                gap: 6px;
            }
            .icon-btn {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                color: var(--text-muted);
                width: 34px;
                height: 34px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
            }
            .icon-btn:hover {
                background: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
            .primary-copy-btn {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%);
                border: 1px solid rgba(16, 185, 129, 0.35);
                color: #a7f3d0;
                padding: 7px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s;
                white-space: nowrap;
            }
            .primary-copy-btn:hover {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(6, 182, 212, 0.3) 100%);
                border-color: #34d399;
                color: #ffffff;
                transform: translateY(-1px);
            }
            .primary-copy-btn.copied {
                background: #10b981;
                color: #041019;
                border-color: #10b981;
            }
            .curl-section {
                margin-top: 24px;
                border-top: 1px solid rgba(255, 255, 255, 0.06);
                padding-top: 20px;
            }
            .curl-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .curl-header span {
                font-size: 12px;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.6px;
            }
            .test-btn {
                background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
                color: white;
                border: none;
                padding: 7px 14px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s;
            }
            .test-btn:hover {
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
                transform: translateY(-1px);
            }
            .curl-box {
                background: rgba(3, 7, 18, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px 14px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: #cbd5e1;
                overflow-x: auto;
                line-height: 1.6;
            }
            .curl-box .hl-k { color: #f43f5e; }
            .curl-box .hl-u { color: #38bdf8; }
            .curl-box .hl-h { color: #fbbf24; }
            .auth-input-group {
                margin-bottom: 20px;
            }
            .auth-input {
                width: 100%;
                background: rgba(3, 7, 18, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 14px 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 18px;
                color: #ffffff;
                text-align: center;
                letter-spacing: 6px;
                text-transform: uppercase;
                transition: all 0.3s;
            }
            .auth-input:focus {
                outline: none;
                border-color: #10b981;
                box-shadow: 0 0 20px rgba(16, 185, 129, 0.25);
            }
            .unlock-btn {
                width: 100%;
                background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
                color: #041019;
                border: none;
                padding: 14px;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3);
                transition: all 0.2s;
            }
            .unlock-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(16, 185, 129, 0.45);
            }
            .hidden { display: none !important; }
            #error-msg {
                color: #f87171;
                font-size: 13px;
                margin-top: 14px;
                text-align: center;
            }
            /* Toast notification */
            .toast-box {
                position: fixed;
                bottom: 25px;
                right: 25px;
                background: #0f172a;
                border: 1px solid #10b981;
                color: #ffffff;
                padding: 12px 20px;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                transform: translateY(100px);
                opacity: 0;
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                z-index: 9999;
            }
            .toast-box.show {
                transform: translateY(0);
                opacity: 1;
            }
            .test-result-box {
                margin-top: 12px;
                background: rgba(3, 7, 18, 0.9);
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                padding: 10px 14px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: #34d399;
                max-height: 120px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        <div class="ambient-mesh"></div>
        <div class="container">
            <!-- LOGIN CARD -->
            <div class="card" id="login-card">
                <div class="header-bar" style="margin-bottom: 28px;">
                    <div class="brand-group">
                        <div class="logo-icon">⚡</div>
                        <div>
                            <div class="brand-title">LMMs Engine</div>
                            <div class="brand-sub">System Security & Gateway</div>
                        </div>
                    </div>
                    <span class="status-pill"><span class="pulse-dot"></span> Port 11435</span>
                </div>
                
                <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px; line-height: 1.5;">
                    Enter the 6-character terminal OTP displayed in your console to securely unlock master credentials.
                </p>

                <div class="auth-input-group">
                    <input type="text" id="otp" class="auth-input" maxlength="6" placeholder="------" autocomplete="off" autofocus>
                </div>
                
                <button class="unlock-btn" onclick="unlock()">Unlock Dashboard</button>
                <div id="error-msg"></div>
            </div>

            <!-- MAIN CREDENTIALS CARD -->
            <div class="card hidden" id="keys-card">
                <div class="header-bar">
                    <div class="brand-group">
                        <div class="logo-icon">⚡</div>
                        <div>
                            <div class="brand-title">LMMs</div>
                            <div class="brand-sub">Universal Cognitive Gateway • MarkanM Edition</div>
                        </div>
                    </div>
                    <span class="status-pill"><span class="pulse-dot"></span> Online</span>
                </div>

                <!-- MODEL & HYBRID LAYER BANNER -->
                <div class="model-banner">
                    <div class="model-top">
                        <span class="model-label">⚡ Active Engine Model</span>
                        <span class="engine-tag">Air Engine Hybrid</span>
                    </div>
                    <div class="model-name" id="display-agent">qwen2.5-1.5b-instruct-q5_k_m</div>
                    <div class="layer-bar-wrap">
                        <div class="layer-bar-info">
                            <span id="gpu-split-text">GPU VRAM: 100% (28 Layers)</span>
                            <span id="cpu-split-text">CPU DDR5: 0% (0 Layers)</span>
                        </div>
                        <div class="split-bar">
                            <div class="split-gpu" id="split-gpu-bar" style="width: 100%;"></div>
                            <div class="split-cpu" id="split-cpu-bar" style="width: 0%;"></div>
                        </div>
                    </div>
                </div>

                <!-- LIVE HARDWARE TELEMETRY -->
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="stat-title">GPU VRAM</div>
                        <div class="stat-val" id="vram-val">-- <span class="stat-sub">/ -- GB</span></div>
                        <div class="meter-bar"><div class="meter-fill" id="vram-meter" style="width: 0%;"></div></div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-title">System RAM (DDR5)</div>
                        <div class="stat-val" id="ram-val">-- <span class="stat-sub">/ -- GB</span></div>
                        <div class="meter-bar"><div class="meter-fill violet" id="ram-meter" style="width: 0%;"></div></div>
                    </div>
                </div>

                <!-- MASTER API KEY -->
                <div class="field-group">
                    <div class="field-label">
                        <span>Master API Key</span>
                        <span class="field-badge">MarkanM Auth</span>
                    </div>
                    <div class="input-box">
                        <div class="code-text" id="api-key-text">MarkanM-sk-••••••••••••••••••••••••••••••••</div>
                        <div class="action-btn-group">
                            <button class="icon-btn" onclick="toggleKeyVisibility()" title="Toggle visibility" id="eye-btn">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            </button>
                            <button class="primary-copy-btn" id="btn-copy-key" onclick="copyCred('api_key', 'btn-copy-key')">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                Copy Key
                            </button>
                        </div>
                    </div>
                </div>

                <!-- UNIVERSAL WEBHOOK URL -->
                <div class="field-group">
                    <div class="field-label">
                        <span>LMMs Universal Webhook URL</span>
                        <span class="field-badge" style="color: #34d399; background: rgba(16, 185, 129, 0.1);">Live Gateway</span>
                    </div>
                    <div class="input-box">
                        <div class="code-text" id="webhook-url-text" style="color: #4ade80;">http://localhost:11435/webhook</div>
                        <div class="action-btn-group">
                            <button class="primary-copy-btn" id="btn-copy-webhook" onclick="copyCred('webhook_url', 'btn-copy-webhook')">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                Copy URL
                            </button>
                        </div>
                    </div>
                </div>

                <!-- CURL SNIPPET & INTERACTIVE TESTER -->
                <div class="curl-section">
                    <div class="curl-header">
                        <span>1-Click Terminal cURL Test</span>
                        <button class="test-btn" id="test-webhook-btn" onclick="triggerTestPing()">⚡ Send Test Ping</button>
                    </div>
                    <div class="curl-box" id="curl-display">
                        <span class="hl-k">curl</span> -X POST <span class="hl-u">http://localhost:11435/webhook</span> \\<br>
                        &nbsp;&nbsp;-H <span class="hl-h">"Authorization: Bearer <span id="curl-key-placeholder">MarkanM-sk-...</span>"</span> \\<br>
                        &nbsp;&nbsp;-H <span class="hl-h">"Content-Type: application/json"</span> \\<br>
                        &nbsp;&nbsp;-d '{"messages":[{"role":"user","content":"Hello LMMs"}]}'
                    </div>
                    <div id="test-result" class="test-result-box hidden"></div>
                </div>
            </div>
        </div>

        <div class="toast-box" id="toast">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            <span id="toast-text">Copied to clipboard!</span>
        </div>

        <script>
            let authToken = "";
            let secureCache = {};
            let isKeyMasked = true;

            document.getElementById("otp").addEventListener("keyup", function(e) {
                if (e.key === "Enter") unlock();
            });

            async function unlock() {
                const otp = document.getElementById("otp").value.trim().toUpperCase();
                if (!otp) return;
                
                try {
                    const res = await fetch("/v1/auth/unlock", {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ otp })
                    });
                    if (!res.ok) {
                        document.getElementById("error-msg").innerText = "Invalid OTP. Check your terminal.";
                        return;
                    }
                    const data = await res.json();
                    authToken = data.token;
                    
                    const keysRes = await fetch("/v1/auth/keys", {
                        headers: { "Authorization": "Bearer " + authToken }
                    });
                    const keys = await keysRes.json();
                    secureCache = keys;
                    
                    // Switch views
                    document.getElementById("login-card").classList.add("hidden");
                    document.getElementById("keys-card").classList.remove("hidden");
                    
                    // Render details
                    document.getElementById("display-agent").innerText = keys.agent_name || "LMMs Hybrid Air Engine";
                    document.getElementById("webhook-url-text").innerText = keys.webhook_url;
                    
                    updateKeyDisplay();
                    
                    // Update telemetry
                    if (keys.hardware) {
                        const hw = keys.hardware;
                        document.getElementById("vram-val").innerHTML = `${hw.vram_used} <span class="stat-sub">/ ${hw.vram_total} GB</span>`;
                        document.getElementById("vram-meter").style.width = Math.min(100, hw.vram_pct) + "%";
                        
                        document.getElementById("ram-val").innerHTML = `${hw.ram_used} <span class="stat-sub">/ ${hw.ram_total} GB</span>`;
                        document.getElementById("ram-meter").style.width = Math.min(100, hw.ram_pct) + "%";
                    }

                    if (keys.model_stats && keys.model_stats.gpu_pct !== undefined) {
                        const gpuP = keys.model_stats.gpu_pct;
                        const cpuP = 100 - gpuP;
                        document.getElementById("split-gpu-bar").style.width = gpuP + "%";
                        document.getElementById("split-cpu-bar").style.width = cpuP + "%";
                        document.getElementById("gpu-split-text").innerText = `GPU VRAM: ${gpuP.toFixed(1)}%`;
                        document.getElementById("cpu-split-text").innerText = `CPU DDR5: ${cpuP.toFixed(1)}%`;
                    }
                    
                    document.getElementById("curl-key-placeholder").innerText = keys.api_key;
                } catch(e) {
                    document.getElementById("error-msg").innerText = "Error connecting to LMMs server.";
                }
            }

            function updateKeyDisplay() {
                const textElem = document.getElementById("api-key-text");
                const fullKey = secureCache.api_key || "";
                if (isKeyMasked) {
                    const prefix = fullKey.substring(0, 11); // MarkanM-sk-
                    textElem.innerText = prefix + "•".repeat(32);
                } else {
                    textElem.innerText = fullKey;
                }
            }

            function toggleKeyVisibility() {
                isKeyMasked = !isKeyMasked;
                updateKeyDisplay();
                const btn = document.getElementById("eye-btn");
                btn.innerHTML = isKeyMasked 
                    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
                    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
            }

            function copyCred(type, btnId) {
                const val = secureCache[type] || document.getElementById(type === "webhook_url" ? "webhook-url-text" : "api-key-text").innerText;
                navigator.clipboard.writeText(val).then(() => {
                    showToast(type === "api_key" ? "Master API Key Copied!" : "Webhook URL Copied!");
                    const btn = document.getElementById(btnId);
                    const originalText = btn.innerHTML;
                    btn.classList.add("copied");
                    btn.innerHTML = `✓ Copied!`;
                    setTimeout(() => {
                        btn.classList.remove("copied");
                        btn.innerHTML = originalText;
                    }, 2000);
                });
            }

            function showToast(msg) {
                const toast = document.getElementById("toast");
                document.getElementById("toast-text").innerText = msg;
                toast.classList.add("show");
                setTimeout(() => toast.classList.remove("show"), 2500);
            }

            async function triggerTestPing() {
                const resBox = document.getElementById("test-result");
                const btn = document.getElementById("test-webhook-btn");
                btn.innerText = "⏳ Testing...";
                resBox.classList.remove("hidden");
                resBox.innerText = "Sending test ping to http://localhost:11435/webhook...";
                
                const t0 = performance.now();
                try {
                    const res = await fetch("/webhook", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": "Bearer " + secureCache.api_key
                        },
                        body: JSON.stringify({
                            messages: [{ role: "user", content: "Ping from LMMs Dashboard" }]
                        })
                    });
                    const duration = Math.round(performance.now() - t0);
                    if (res.ok) {
                        const json = await res.json();
                        resBox.innerHTML = `✓ Status: ${res.status} OK (${duration}ms)<br>${JSON.stringify(json, null, 2)}`;
                    } else {
                        resBox.innerHTML = `⚠ HTTP ${res.status} (${duration}ms): ${res.statusText}`;
                    }
                } catch(err) {
                    resBox.innerHTML = `✕ Test Error: ${err.message}`;
                } finally {
                    btn.innerText = "⚡ Send Test Ping";
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/v1/auth/unlock")
async def unlock_dashboard(req: UnlockRequest):
    global server_otp, server_temp_token
    if req.otp == server_otp:
        server_temp_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        return {"token": server_temp_token}
    raise HTTPException(status_code=401, detail="Invalid OTP")

@app.get("/v1/auth/keys")
async def get_keys(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer ") or auth_header.split(" ")[1] != server_temp_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    global active_agent_name, server_api_key
    model_name = active_agent_name or "qwen2.5-1.5b-instruct-q5_k_m"
    model_stats = {}
    try:
        active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
        if os.path.exists(active_f):
            with open(active_f, "r") as f: d = json.load(f)
            if d: 
                model_name = list(d.keys())[0]
                model_stats = d.get(model_name, {})
    except Exception: pass

    # Hardware stats
    import psutil
    sys_ram = psutil.virtual_memory()
    ram_total = round(sys_ram.total / (1024**3), 1)
    ram_used = round(sys_ram.used / (1024**3), 1)
    ram_pct = round(sys_ram.percent, 1)

    vram_total = 0.0
    vram_used = 0.0
    vram_pct = 0.0
    try:
        import torch
        if torch.cuda.is_available():
            vram_total = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
            vram_used = round(torch.cuda.memory_allocated(0) / (1024**3), 1)
            vram_pct = round((vram_used / max(vram_total, 0.1)) * 100, 1)
    except Exception:
        pass

    return {
        "api_key": server_api_key,
        "webhook_url": "http://localhost:11435/webhook",
        "agent_name": model_name,
        "model_stats": model_stats,
        "hardware": {
            "vram_total": vram_total,
            "vram_used": vram_used,
            "vram_pct": vram_pct,
            "ram_total": ram_total,
            "ram_used": ram_used,
            "ram_pct": ram_pct,
            "cpu_cores": psutil.cpu_count(logical=False) or 4,
            "cpu_pct": psutil.cpu_percent(interval=None)
        }
    }


def run_server(port: int = 11435):
    global server_otp, server_api_key
    server_otp = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    server_api_key = "MarkanM-sk-" + ''.join(random.choices(string.ascii_letters + string.digits, k=48))
    
    print(f"===========================================================")
    print(f"             LMMs Secure API Server Started                ")
    print(f"       Powered by MarkanM. For more details: Lmms.markanm.com")
    print(f"===========================================================")
    print(f" -> Dashboard: http://localhost:{port}/dashboard")
    print(f"")
    print(f" [SECURITY] Terminal OTP: {server_otp}")
    print(f" Enter this OTP in the dashboard to unlock credentials.")
    print(f"===========================================================")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    run_server()

