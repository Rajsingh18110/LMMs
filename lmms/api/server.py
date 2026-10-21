"""
LMMs API Server
Primary HTTP/WebSocket Gateway for the 3-Tier (Air+LlamaCpp, Air+PyTorch, Unified Super Engine) LMMs System.
"""

from __future__ import annotations

import os
import sys
import time
import signal
import threading
import argparse
import uvicorn
from typing import Dict, Any, Optional

from lmms.api.app import app
from lmms.engine.manager import engine_manager
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


def run_server(
    host: str = "0.0.0.0",
    port: int = 11435,
    reload: bool = False,
    idle_timeout: Optional[int] = None,
    engine_tier: Optional[int] = None
) -> None:
    """Launch the LMMs API Server with security tokens and interactive terminal banner."""
    if engine_tier:
        try:
            engine_manager.set_engine_mode(str(engine_tier))
        except Exception:
            pass

    tier_info = engine_manager.get_tier_info()
    creds = initialize_security_credentials()
    otp = creds["otp"]

    app.state.client_connected = False
    app.state.last_active_time = time.time()

    print("==================================================================")
    print("                 LMMs Secure Super Engine Server                  ")
    print(f"       {tier_info['name']}")
    print("==================================================================")
    print(f" -> Local Dashboard: http://localhost:{port}/dashboard")
    print(f" -> API Base URL:    http://{host}:{port}/v1")
    print(f" -> OpenAPI Docs:    http://localhost:{port}/docs")
    print("")
    print(f" [SECURITY] Terminal OTP: \033[1;32m{otp}\033[0m")
    print(" Enter this OTP in the dashboard or via client to unlock access.")
    if idle_timeout and idle_timeout > 0:
        print(f" [TIMEOUT]  Idle auto-stop armed ({idle_timeout}s timeout if no client connects)")
    print("==================================================================")

    from lmms.common.discovery import start_lan_beacon
    start_lan_beacon(port=port)

    # Idle timeout watchdog for interactive foreground sessions
    if idle_timeout and idle_timeout > 0:
        start_ts = time.time()

        def _timeout_watcher():
            time.sleep(15)  # initial grace period
            while True:
                time.sleep(5)
                if getattr(app.state, "client_connected", False):
                    # Client has authenticated/connected, stop monitoring timeout
                    break
                elapsed = time.time() - start_ts
                if elapsed > idle_timeout:
                    print(f"\n\033[1;33m[TIMEOUT]\033[0m No client connected within {idle_timeout}s. Automatically stopping interactive server to free resources.")
                    os.kill(os.getpid(), signal.SIGINT)
                    break

        threading.Thread(target=_timeout_watcher, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="warning", reload=reload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LMMs 3-Tier API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Binding network interface host")
    parser.add_argument("--port", type=int, default=11435, help="Port to listen on (default: 11435)")
    parser.add_argument("--reload", action="store_true", help="Enable hot reload for development")
    parser.add_argument("--timeout", type=int, default=None, help="Idle timeout in seconds (auto-shutdown if no client connects)")
    parser.add_argument("--tier", type=int, default=3, choices=[1, 2, 3], help="Engine tier: 1 (llama.cpp+Air), 2 (PyTorch+Air), 3 (Unified Super Engine)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, reload=args.reload, idle_timeout=args.timeout, engine_tier=args.tier)
