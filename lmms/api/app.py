from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lmms.api.routes import (
    models_router,
    chat_router,
    air_router,
    engine_router,
    discovery_router,
    dashboard_router,
)


def create_app() -> FastAPI:
    """FastAPI Application factory for LMMs Dual-Engine Server."""
    app = FastAPI(
        title="LMMs Engine API",
        version="2.5.0-native",
        description="Unified Dual-Engine (Air+LlamaCpp & Air+PyTorch) Local & LAN Inference Server",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS support for LAN clients & Web Dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount modular route handlers
    app.include_router(chat_router)
    app.include_router(models_router)
    app.include_router(air_router)
    app.include_router(engine_router)
    app.include_router(discovery_router)
    app.include_router(dashboard_router)

    return app


app = create_app()
