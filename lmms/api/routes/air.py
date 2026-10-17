import os
import json
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lmms.engine.manager import engine_manager
from lmms.api.routes.chat import ChatRequest

router = APIRouter(prefix="/v1/air", tags=["air"])


@router.get("/ps")
def air_ps():
    return engine_manager.air_scheduler.get_ps()


@router.get("/stats")
def air_stats():
    from lmms.engine.air.stats import AirStats
    return AirStats.get_system_stats()


@router.get("/cache")
def air_cache():
    from lmms.engine.registry import RegistryManager
    reg = RegistryManager()

    disk_models = []
    if os.path.exists(reg.models_dir):
        for f in os.listdir(reg.models_dir):
            if f.endswith(".gguf"):
                disk_models.append(f.replace(".gguf", ""))

    vram_models = [m["model"] for m in engine_manager.air_scheduler.get_ps() if m.get("vram_gb", 0) > 0]
    ram_models = engine_manager.air_ram_cache.get_models()

    return {
        "vram_models": vram_models,
        "ram_models": ram_models,
        "disk_models": [m for m in disk_models if m not in vram_models and m not in ram_models]
    }


@router.post("/generate")
def air_generate(req: ChatRequest):
    model_name = req.model_name

    from lmms.engine.registry import RegistryManager
    reg = RegistryManager()
    path = os.path.join(reg.models_dir, f"{model_name}.gguf")

    if not os.path.exists(path):
        try:
            downloads_file = os.path.expanduser("~/.lmms/logs/downloads.json")
            if os.path.exists(downloads_file):
                with open(downloads_file, "r") as f:
                    d = json.load(f)
                if model_name in d and d[model_name].get("file"):
                    path = os.path.join(reg.models_dir, d[model_name]["file"])
        except Exception:
            pass

    if not os.path.exists(path):
        search_term = model_name.replace(":", "-").lower()
        if os.path.exists(reg.models_dir):
            for f in os.listdir(reg.models_dir):
                if f.endswith(".gguf") and search_term in f.lower():
                    path = os.path.join(reg.models_dir, f)
                    break

    if not os.path.exists(path):
        manifest_path = os.path.join(reg.manifests_dir, f"{model_name}.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                data = json.load(f)
                base = data.get("base_model", "")
                path = os.path.join(reg.models_dir, f"{base}.gguf") if not base.endswith(".gguf") else os.path.join(reg.models_dir, base)

    if os.path.exists(path):
        size_gb = os.path.getsize(path) / (1024**3)
        if not engine_manager.air_swapper.ensure_vram_capacity(size_gb):
            raise HTTPException(status_code=507, detail="Insufficient VRAM to load this model, even after eviction.")

        success = engine_manager.engine_1.load_model(path)
        if not success:
            raise HTTPException(status_code=500, detail="Engine failed to load model into VRAM.")

        if model_name in engine_manager.air_scheduler.active_models:
            if engine_manager.air_scheduler.active_models[model_name]["location"] != "VRAM":
                engine_manager.air_swapper.swap_to_vram(model_name)
        else:
            engine_manager.air_scheduler.register_model(model_name, "VRAM", size_gb, 0.0)

    engine_manager.air_scheduler.update_state(model_name, "Generating")

    def stream_air():
        try:
            for chunk in engine_manager.engine_1.generate({"messages": req.messages}, stream=True):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            engine_manager.air_scheduler.update_state(model_name, "Keep Warm")

    return StreamingResponse(stream_air(), media_type="text/plain")
