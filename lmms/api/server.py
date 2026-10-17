"""
LMMs API Server
Primary HTTP/WebSocket Gateway for the Dual-Engine (Air+LlamaCpp & Air+PyTorch) LMMs System.
"""

from __future__ import annotations

import argparse
import uvicorn
from typing import Dict, Any, Optional

from lmms.api.app import app
from lmms.api.routes.dashboard import initialize_security_credentials, server_otp, server_api_key
from lmms.api.routes.models import (
    LoadRequest,
    UnloadRequest,
    PullRequest,
    download_model_task,
    load_model,
    unload_model,
    list_models,
    ps_models,
    info_model,
    delete_model,
    search_models,
    pull_model,
)
from lmms.api.routes.chat import ChatRequest, chat_completions
from lmms.api.routes.engine import DoctorRequest, engine_doctor, run_benchmark
from lmms.api.routes.air import air_ps, air_stats, air_cache, air_generate
from lmms.api.routes.discovery import webhook_get, webhook_post, ping, health
from lmms.api.routes.dashboard import UnlockRequest, serve_dashboard, unlock_dashboard, get_keys


def run_server(host: str = "0.0.0.0", port: int = 11435, reload: bool = False) -> None:
    """Launch the LMMs API Server with security tokens and interactive terminal banner."""
    creds = initialize_security_credentials()
    otp = creds["otp"]

    print("===========================================================")
    print("             LMMs Secure API Server Started                ")
    print("       Dual-Engine Architecture: Air+LlamaCpp & Air+PyTorch")
    print("===========================================================")
    print(f" -> Local Dashboard: http://localhost:{port}/dashboard")
    print(f" -> API Base URL:    http://{host}:{port}/v1")
    print(f" -> OpenAPI Docs:    http://localhost:{port}/docs")
    print("")
    print(f" [SECURITY] Terminal OTP: {otp}")
    print(" Enter this OTP in the dashboard to unlock credentials.")
    print("===========================================================")

    uvicorn.run(app, host=host, port=port, log_level="warning", reload=reload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LMMs Dual-Engine API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding network interface host")
    parser.add_argument("--port", type=int, default=11435, help="Port to listen on (default: 11435)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload for development")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, reload=args.reload)
