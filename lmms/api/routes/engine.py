import os
import sys
import shutil
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lmms.engine.manager import engine_manager

router = APIRouter(prefix="/v1", tags=["engine"])

MODELS_DIR = os.path.expanduser("~/.lmms/models")


class EngineModeRequest(BaseModel):
    mode: str


class DoctorRequest(BaseModel):
    fix: bool = False


@router.get("/engine/mode")
async def get_engine_mode():
    return {
        "active_mode": engine_manager.active_mode,
        "modes": {
            "auto": "Dynamic dispatch based on model architecture and hardware",
            "1": "Engine 1: Air Engine + Llama.cpp (GGUF High-Throughput & Hybrid Offload)",
            "2": "Engine 2: Air Engine + PyTorch (HuggingFace Safetensors, Multimodal & Training)"
        }
    }


@router.post("/engine/mode")
async def set_engine_mode(req: EngineModeRequest):
    try:
        new_mode = engine_manager.set_engine_mode(req.mode)
        return {
            "status": "success",
            "active_mode": new_mode,
            "message": f"Engine mode set to '{new_mode}'"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/engine/status")
async def get_engine_status():
    return engine_manager.status()


class TokenizeRequest(BaseModel):
    model_name: Optional[str] = None
    texts: List[str]


@router.get("/model/context")
async def get_model_context(model_name: Optional[str] = None):
    ctx_len = 8192
    if engine_manager.runtime and hasattr(engine_manager.runtime, "pager") and engine_manager.runtime.pager.active_profile:
        ctx_len = engine_manager.runtime.pager.active_profile.context_length
    elif model_name:
        path = os.path.join(MODELS_DIR, f"{model_name}.gguf")
        if not os.path.exists(path) and os.path.exists(model_name):
            path = model_name
        if os.path.exists(path):
            try:
                from lmms.engine.engine_1_llamacpp.air_loader import parse_gguf_metadata
                meta = parse_gguf_metadata(path)
                for k, v in meta.items():
                    if k.endswith(".context_length") and isinstance(v, int) and v > 0:
                        ctx_len = v
                        break
            except Exception:
                pass
    return {
        "status": "success",
        "model_name": model_name or "active",
        "context_length": ctx_len
    }


@router.post("/tokenize")
async def tokenize_texts(req: TokenizeRequest):
    counts = []
    runtime = engine_manager.runtime
    for text in req.texts:
        count = None
        if runtime and hasattr(runtime, "tokenize"):
            try:
                tokens = runtime.tokenize(text)
                if tokens:
                    count = len(tokens)
            except Exception:
                pass
        if count is None:
            count = max(1, int(len(text) / 3.2) + 1)
        counts.append(count)
    return {
        "status": "success",
        "token_counts": counts
    }



@router.get("/benchmark")
async def run_benchmark():
    try:
        from lmms.engine.benchmark import BenchmarkEngine
        results = BenchmarkEngine().run_benchmarks({"vram_total_mb": 6000})
        return {"status": "success", "benchmarks": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/doctor")
async def engine_doctor(req: DoctorRequest):
    report: Dict[str, Any] = {
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
    except Exception:
        pass

    if os.path.exists(MODELS_DIR):
        total, used, free = shutil.disk_usage(MODELS_DIR)
        report["disk_available_gb"] = round(free / (1024**3), 2)

    try:
        import llama_cpp  # type: ignore
        report["llama_cpp_python"] = True
    except Exception:
        pass

    try:
        import torch
        report["cuda_support"] = torch.cuda.is_available()
    except Exception:
        pass

    fixes_applied: List[str] = []
    if req.fix:
        if not report["models_dir_exists"]:
            os.makedirs(MODELS_DIR, exist_ok=True)
            report["models_dir_exists"] = True
            report["models_dir_writable"] = True
            fixes_applied.append("Created ~/.lmms/models/")

        if not report["cuda_support"]:
            fixes_applied.append("SUGGESTION: Run `CMAKE_ARGS='-DGGML_CUDA=on' pip install llama-cpp-python --upgrade --force-reinstall --no-cache-dir`")

        engine_manager.runtime.unload_model()
        engine_manager.pytorch_runtime.unload_model()
        fixes_applied.append("Cleared VRAM cache and unloaded models.")

    return {"report": report, "fixes": fixes_applied}
