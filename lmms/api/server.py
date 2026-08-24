import os
import json
import threading
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import asyncio
from huggingface_hub import hf_hub_download

from lmms.engine.manager import engine_manager

app = FastAPI(title="LMMs Engine API")

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

class ChatRequest(BaseModel):
    model_name: str
    messages: List[Dict[str, str]]
    stream: bool = True
    mode: Optional[str] = "deep"
    think: Optional[bool] = True

class DoctorRequest(BaseModel):
    fix: bool = False

class TokenizeRequest(BaseModel):
    model_name: str
    text: str

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
    success = engine_manager.runtime.load_model(path)
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
def air_generate(req: ChatRequest):
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
        success = engine_manager.runtime.load_model(path)
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
        engine_manager.runtime.unload_model(model_name)
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

def download_model_task(model_name: str):
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
                "gemma4": "bartowski/gemma-2-2b-it-GGUF",
                "gemma": "bartowski/gemma-2-2b-it-GGUF",
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

        class DownloadTqdm(original_tqdm):
            def update(self, n=1):
                super().update(n)
                if hasattr(self, 'total') and self.total:
                    pct = int((self.n / self.total) * 100)
                    speed = getattr(self, 'format_dict', {}).get('rate', 0)
                    speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else ""
                    size_str = f"{self.n / 1024 / 1024 / 1024:.2f}G/{self.total / 1024 / 1024 / 1024:.2f}G"
                    
                    try:
                        with open(downloads_file, "r") as file: d = json.load(file)
                        d[model_name]["status"] = f"{pct}% ({size_str} @ {speed_str})"
                        with open(downloads_file, "w") as file: json.dump(d, file)
                    except Exception: pass

        _tqdm.tqdm = DownloadTqdm
        
        try:
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
    background_tasks.add_task(download_model_task, req.model_name)
    return {"status": "downloading", "model": req.model_name}

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
        tokens = engine_manager.runtime.tokenize(req.text)
        return {"status": "success", "token_count": len(tokens)}
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
                success = engine_manager.runtime.load_model(path)
                if not success:
                    engine_manager.cache.unload_model(req.model_name)
                    raise HTTPException(status_code=500, detail="Failed to load model. Is llama-cpp-python installed?")
                runtime = engine_manager.runtime
            else:
                raise HTTPException(status_code=507, detail="Insufficient memory to auto-load")
        else:
            # Fallback to PyTorch Runtime
            success = engine_manager.pytorch_runtime.load_model(req.model_name)
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
                        {"messages": req.messages, "mode": req.mode, "think": req.think}, 
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
            {"messages": req.messages, "mode": req.mode, "think": req.think}, 
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
        <title>LMMs Engine Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
        <style>
            body { 
                font-family: 'Inter', sans-serif; 
                background: radial-gradient(circle at 10% 20%, rgb(14, 14, 25) 0%, rgb(0, 0, 0) 90%);
                color: #ffffff; 
                display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; 
                overflow: hidden;
            }
            /* Ambient background glow */
            .glow {
                position: absolute;
                width: 600px; height: 600px;
                background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, rgba(0,0,0,0) 70%);
                top: -200px; left: -200px;
                border-radius: 50%;
                z-index: -1;
            }
            .card { 
                background: rgba(20, 20, 30, 0.5); 
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08); 
                border-radius: 16px; 
                padding: 40px; width: 450px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.8), inset 0 0 15px rgba(255,255,255,0.02); 
            }
            h2 { 
                margin-top: 0; 
                background: linear-gradient(90deg, #4ade80, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800;
                font-size: 28px;
                margin-bottom: 25px;
            }
            .form-group { margin-bottom: 25px; }
            label { display: block; font-size: 13px; margin-bottom: 10px; color: #a1a1aa; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;}
            input[type="text"] { 
                width: 100%; padding: 12px 15px; 
                background-color: rgba(0, 0, 0, 0.5); 
                border: 1px solid rgba(255, 255, 255, 0.1); 
                border-radius: 8px; color: #fff; font-size: 16px; box-sizing: border-box; 
                transition: all 0.3s ease;
            }
            input[type="text"]:focus {
                border-color: #3b82f6;
                box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
                outline: none;
            }
            button { 
                width: 100%; padding: 14px; 
                background: linear-gradient(45deg, #3b82f6, #8b5cf6); 
                color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600;
                cursor: pointer; transition: all 0.3s ease; 
                box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
            }
            button:hover { 
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
            }
            .hidden { display: none !important; }
            canvas { 
                background-color: rgba(0,0,0,0.6); 
                border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); 
                margin-bottom: 15px; padding: 10px; cursor: crosshair; 
                box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
            }
            .copy-btn { 
                width: auto; padding: 6px 12px; font-size: 12px; 
                background: rgba(255,255,255,0.1); color: #fff; 
                border-radius: 6px; margin-bottom: 25px; 
                box-shadow: none; border: 1px solid rgba(255,255,255,0.1);
            }
            .copy-btn:hover {
                background: rgba(255,255,255,0.2);
                transform: translateY(0);
                box-shadow: none;
            }
            .agent-name { 
                color: #facc15; font-weight: 600; margin-bottom: 25px; 
                padding: 10px; background: rgba(250, 204, 21, 0.1); 
                border-radius: 8px; border: 1px solid rgba(250, 204, 21, 0.2);
                display: inline-block;
            }
            #error-msg { color: #f87171; font-size: 14px; margin-top: 15px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="glow"></div>
        <div class="card" id="login-card">
            <h2>System Authentication</h2>
            <div class="form-group">
                <label for="otp">Terminal OTP</label>
                <input type="text" id="otp" placeholder="Enter 6-character code" autocomplete="off">
            </div>
            <button onclick="unlock()">Unlock Engine Dashboard</button>
            <div id="error-msg"></div>
        </div>

        <div class="card hidden" id="keys-card">
            <h2>LMMs Credentials</h2>
            <div class="agent-name" id="display-agent">System Offline</div>
            
            <label>Master API Key (Encrypted View)</label>
            <canvas id="canvas-api-key" width="370" height="40"></canvas>
            <button class="copy-btn" onclick="copyKey('api_key')">Copy API Key</button>
            
            <label>Universal Webhook URL</label>
            <canvas id="canvas-webhook" width="370" height="40"></canvas>
            <button class="copy-btn" onclick="copyKey('webhook_url')">Copy Webhook</button>
        </div>

        <script>
            let authToken = "";
            let secureCache = {};

            async function unlock() {
                const otp = document.getElementById("otp").value;
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
                
                document.getElementById("login-card").classList.add("hidden");
                document.getElementById("keys-card").classList.remove("hidden");
                
                document.getElementById("display-agent").innerText = "Active Model: " + keys.agent_name;
                
                drawToCanvas("canvas-api-key", keys.api_key);
                drawToCanvas("canvas-webhook", keys.webhook_url);
            }

            function drawToCanvas(canvasId, text) {
                const canvas = document.getElementById(canvasId);
                const ctx = canvas.getContext("2d");
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "#4ade80";
                ctx.font = "15px Consolas, monospace";
                ctx.fillText(text, 10, 25);
            }

            function copyKey(keyType) {
                if (secureCache[keyType]) {
                    navigator.clipboard.writeText(secureCache[keyType])
                        .then(() => alert("Copied securely!"))
                        .catch(err => alert("Copy failed: " + err));
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
    try:
        active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
        if os.path.exists(active_f):
            with open(active_f, "r") as f: d = json.load(f)
            if d: active_agent_name = list(d.keys())[0]
    except Exception: pass
        
    return {
        "api_key": server_api_key,
        "webhook_url": "http://localhost:11435/webhook",
        "agent_name": active_agent_name
    }


def run_server(port: int = 11435):
    global server_otp, server_api_key
    server_otp = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    server_api_key = "lmms-sk-" + ''.join(random.choices(string.ascii_letters + string.digits, k=48))
    
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
