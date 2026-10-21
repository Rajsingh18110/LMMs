import os
import json
from typing import Dict, Any, List
from fastapi import APIRouter

from lmms.engine.manager import engine_manager
from lmms.api.routes.chat import ChatRequest, chat_completions

router = APIRouter(tags=["discovery"])


@router.get("/webhook")
async def webhook_get():
    """LAN and auto-discovery heartbeat probe."""
    try:
        active_f = os.path.expanduser("~/.lmms/logs/active_models.json")
        if os.path.exists(active_f):
            with open(active_f, "r") as f:
                d = json.load(f)
            return {"active_models": list(d.keys()), "engine": "running"}
    except Exception:
        pass

    loaded = list(engine_manager.get_loaded_models().keys())
    return {"active_models": loaded, "engine": "running"}


@router.post("/webhook")
async def webhook_post(req: ChatRequest):
    """Direct webhook routing into chat completions."""
    return await chat_completions(req)


@router.get("/ping")
@router.post("/ping")
@router.get("/v1/ping")
@router.post("/v1/ping")
@router.get("/v1/internal/ping")
@router.post("/v1/internal/ping")
async def ping():
    """Ultra-fast probe for CLI remote scanner and persistent client keepalive."""
    tier_info = engine_manager.get_tier_info()
    return {
        "status": "pong",
        "engine": "lmms",
        "version": "2.5.0-native",
        "mode": "persistent",
        "active_mode": engine_manager.active_mode,
        "tier": tier_info["tier"],
        "tier_name": tier_info["name"],
        "models_count": len(engine_manager.get_loaded_models())
    }


@router.get("/health")
@router.get("/v1/health")
async def health():
    """Engine health status."""
    return {
        "status": "healthy",
        "tier": engine_manager.get_tier_info(),
        "manager": engine_manager.status()
    }
