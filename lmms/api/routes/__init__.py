"""
LMMs API Route Modules
Modular FastAPI routers for models, chat, air engine, discovery, telemetry, and web dashboard.
"""

from .models import router as models_router
from .chat import router as chat_router
from .air import router as air_router
from .engine import router as engine_router
from .discovery import router as discovery_router
from .dashboard import router as dashboard_router

__all__ = [
    "models_router",
    "chat_router",
    "air_router",
    "engine_router",
    "discovery_router",
    "dashboard_router",
]
