import os
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    hf_hub_download = None

from lmms.engine.manager import engine_manager

router = APIRouter(prefix="/v1/models", tags=["models"])

MODELS_DIR = os.path.expanduser("~/.lmms/models")
os.makedirs(MODELS_DIR, exist_ok=True)


class LoadRequest(BaseModel):
    model_name: str
    model_path: Optional[str] = None


class UnloadRequest(BaseModel):
    model_name: str


class PullRequest(BaseModel):
    model_name: str


def download_model_task(model_name: str):
    try:
        from huggingface_hub import HfApi
        api = HfApi()
        if "/" in model_name:
            repo_id = model_name
        else:
            search_term = model_name.replace(":", "-")
            models = list(api.list_models(search=search_term, filter="gguf", limit=1))
            if models:
                repo_id = models[0].id
            else:
                downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
                try:
                    with open(downloads_file, "r") as f:
                        state = json.load(f)
                    state[model_name] = {"status": "failed (not found)", "repo": model_name, "file": ""}
                    with open(downloads_file, "w") as f:
                        json.dump(state, f)
                except Exception:
                    pass
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

        downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
        os.makedirs(os.path.dirname(downloads_file), exist_ok=True)
        state = {}
        if os.path.exists(downloads_file):
            try:
                with open(downloads_file, "r") as f:
                    state = json.load(f)
            except Exception:
                pass

        state[model_name] = {"status": "0%", "repo": repo_id, "file": target_file}
        with open(downloads_file, "w") as f:
            json.dump(state, f)

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
                        with open(downloads_file, "r") as file:
                            d = json.load(file)
                        d[model_name]["status"] = f"{pct}% ({size_str} @ {speed_str})"
                        with open(downloads_file, "w") as file:
                            json.dump(d, file)
                    except Exception:
                        pass

        _tqdm.tqdm = DownloadTqdm

        try:
            if hf_hub_download is not None:
                hf_hub_download(repo_id=repo_id, filename=target_file, local_dir=MODELS_DIR)
            else:
                raise RuntimeError("huggingface_hub is not installed.")
            try:
                with open(downloads_file, "r") as f:
                    state = json.load(f)
                state[model_name]["status"] = "complete"
                with open(downloads_file, "w") as f:
                    json.dump(state, f)
            except Exception:
                pass
        finally:
            _tqdm.tqdm = original_tqdm

        print("Download complete.")
    except Exception as e:
        downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
        try:
            with open(downloads_file, "r") as f:
                state = json.load(f)
            state[model_name] = {"status": "failed", "error": str(e)}
            with open(downloads_file, "w") as f:
                json.dump(state, f)
        except Exception:
            pass
        print(f"Download failed: {e}")


@router.post("/load")
async def load_model(req: LoadRequest):
    path = req.model_path
    if not path or not os.path.exists(path):
        candidate = os.path.join(MODELS_DIR, f"{req.model_name}.gguf")
        if os.path.exists(candidate):
            path = candidate
        elif os.path.exists(os.path.join(MODELS_DIR, req.model_name)):
            path = os.path.join(MODELS_DIR, req.model_name)
        elif os.path.exists(req.model_name):
            path = req.model_name
        else:
            raise HTTPException(status_code=404, detail=f"Model file not found: {req.model_name}")

    size_gb = os.path.getsize(path) / (1024**3)

    if not engine_manager.cache.can_fit(size_gb):
        raise HTTPException(status_code=507, detail="Insufficient VRAM/RAM to load model")

    engine_manager.cache.load_model(req.model_name, size_gb)
    runtime = engine_manager.get_runtime(req.model_name)
    try:
        success = runtime.load_model(path)
    except Exception as e:
        engine_manager.cache.unload_model(req.model_name)
        raise HTTPException(status_code=500, detail=f"Failed to initialize runtime: {e}")

    if not success:
        engine_manager.cache.unload_model(req.model_name)
        raise HTTPException(status_code=500, detail="Failed to initialize runtime")

    return {"status": "success", "stats": engine_manager.cache.get_stats()}


@router.post("/unload")
def unload_model(req: UnloadRequest):
    engine_manager.runtime.unload_model()
    engine_manager.pytorch_runtime.unload_model()
    engine_manager.cache.unload_model(req.model_name)
    engine_manager.air_scheduler.remove_model(req.model_name)
    return {"status": "success", "message": f"Model {req.model_name} unloaded."}


@router.get("/list")
async def list_models():
    models = []
    if os.path.exists(MODELS_DIR):
        for file in os.listdir(MODELS_DIR):
            if file.endswith(".gguf"):
                path = os.path.join(MODELS_DIR, file)
                size_gb = os.path.getsize(path) / (1024**3)
                models.append({
                    "name": file.replace(".gguf", ""),
                    "size_gb": round(size_gb, 2)
                })
    return {"models": models}


@router.get("/ps")
async def ps_models():
    return engine_manager.cache.get_stats()


@router.get("/info/{model_name}")
async def info_model(model_name: str):
    path = os.path.join(MODELS_DIR, f"{model_name}.gguf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Model file not found")

    size_gb = os.path.getsize(path) / (1024**3)
    mod_time = os.path.getmtime(path)

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
        "architecture": "llama"
    }


@router.delete("/delete/{model_name}")
async def delete_model(model_name: str):
    path = os.path.join(MODELS_DIR, f"{model_name}.gguf")
    if engine_manager.is_model_loaded(model_name):
        engine_manager.cache.unload_model(model_name)
        engine_manager.runtime.unload_model(model_name)
        engine_manager.pytorch_runtime.unload_model(model_name)
    if os.path.exists(path):
        os.remove(path)
        return {"status": "success", "message": f"Deleted {model_name}"}
    raise HTTPException(status_code=404, detail="Model file not found")


@router.get("/search")
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


@router.post("/pull")
async def pull_model(req: PullRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(download_model_task, req.model_name)
    return {"status": "downloading", "model": req.model_name}
