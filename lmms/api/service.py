"""
LMMs Daemon Service Controller
Manages background and daemon lifecycle for the LMMs API Server.
Supports 3-tier engine architecture:
- Tier 1: llama.cpp + AirEngine (GGUF High-Throughput & Hybrid Offload)
- Tier 2: PyTorch + AirEngine (Safetensors, Multimodal & Training)
- Tier 3: llama.cpp + PyTorch + AirEngine (Unified 3-in-1 Super Engine)
"""

from __future__ import annotations

import os
import sys
import json
import time
import signal
import subprocess
import urllib.request
from typing import Dict, Any, Optional

LMMS_HOME = os.path.expanduser("~/.lmms")
PID_FILE = os.path.join(LMMS_HOME, "server.pid")
META_FILE = os.path.join(LMMS_HOME, "server_meta.json")
LOG_DIR = os.path.join(LMMS_HOME, "logs")
SERVER_LOG = os.path.join(LOG_DIR, "server.log")


def _ensure_dirs():
    os.makedirs(LMMS_HOME, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)


def is_server_running() -> Optional[int]:
    """Returns PID if server is alive, None otherwise."""
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # Check if process is alive
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        # Process dead or stale PID
        for path in (PID_FILE, META_FILE):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        return None


def get_server_metadata() -> Dict[str, Any]:
    """Reads persistent server metadata (forever mode, initiator, engine tier)."""
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def get_ai_python_executable() -> str:
    """Finds the Python interpreter that has AI engine dependencies (llama_cpp, torch) installed."""
    if os.name == "nt":
        venv_py = os.path.expanduser("~/.lmms/app/venv/Scripts/python.exe")
    else:
        venv_py = os.path.expanduser("~/.lmms/app/venv/bin/python")
    if os.path.exists(venv_py):
        return venv_py

    try:
        import llama_cpp  # type: ignore # noqa: F401
        return sys.executable
    except ImportError:
        pass

    for cand in ["python3.11", "/usr/local/bin/python3.11", "python3.12", "python3.10"]:
        try:
            res = subprocess.run([cand, "-c", "import llama_cpp"], capture_output=True)
            if res.returncode == 0:
                return cand
        except Exception:
            pass

    return sys.executable


def wait_for_server_healthy(port: int = 11435, host: str = "127.0.0.1", timeout: float = 8.0) -> bool:
    """Polls server ping/webhook endpoints until server is responsive or timeout expires."""
    target_host = "127.0.0.1" if host in ["0.0.0.0", ""] else host
    probe_url = f"http://{target_host}:{port}/ping"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(probe_url, headers={"User-Agent": "LMMs-Service/2.5.0"})
            with urllib.request.urlopen(req, timeout=0.3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def start_server_daemon(
    port: int = 11435,
    host: str = "0.0.0.0",
    engine_mode: str = "auto",
    engine_tier: Optional[int] = None,
    forever: bool = False,
    initiator: str = "daemon"
) -> Dict[str, Any]:
    """
    Starts the LMMs API Server as a detached background process.
    - Tier 1: llama.cpp + AirEngine (GGUF High-Throughput & Hybrid Offload)
    - Tier 2: PyTorch + AirEngine (Safetensors, Multimodal & Training)
    - Tier 3: llama.cpp + PyTorch + AirEngine (Unified 3-in-1 Super Engine)
    - forever=True: Permanent daemon (started via `lmms server start`) that never auto-exits on CLI/GUI close.
    """
    _ensure_dirs()
    existing_pid = is_server_running()
    if existing_pid:
        meta = get_server_metadata()
        tier_val = meta.get("tier", 3)
        return {
            "status": "already_running",
            "pid": existing_pid,
            "port": meta.get("port", port),
            "host": meta.get("host", host),
            "tier": tier_val,
            "forever": meta.get("forever", forever),
            "initiator": meta.get("initiator", initiator),
            "url": f"http://{host}:{port}"
        }

    # Normalize engine tier mapping
    if engine_tier == 1:
        engine_mode = "1"
    elif engine_tier == 2:
        engine_mode = "2"
    elif engine_tier == 3 or engine_mode in ["auto", "3", "unified", "super"]:
        engine_mode = "auto"
        engine_tier = 3
    else:
        if engine_mode == "1":
            engine_tier = 1
        elif engine_mode == "2":
            engine_tier = 2
        else:
            engine_tier = 3
            engine_mode = "auto"

    env = os.environ.copy()
    if engine_mode:
        env["LMMS_ENGINE_MODE"] = engine_mode

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    curr_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{curr_pp}" if curr_pp else project_root

    python_exe = get_ai_python_executable()

    cmd = [
        python_exe,
        "-m", "lmms.api.server",
        "--host", host,
        "--port", str(port)
    ]

    log_file = open(SERVER_LOG, "a")
    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=env
    )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    metadata = {
        "pid": proc.pid,
        "port": port,
        "host": host,
        "tier": engine_tier,
        "engine_mode": engine_mode,
        "forever": forever,
        "initiator": initiator,
        "started_at": time.time()
    }
    try:
        with open(META_FILE, "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception:
        pass

    # Wait for the server to be responsive
    healthy = wait_for_server_healthy(port=port, host=host, timeout=5.0)

    tier_names = {
        1: "Tier 1: llama.cpp + AirEngine (GGUF High-Throughput & Hybrid Offload)",
        2: "Tier 2: PyTorch + AirEngine (Safetensors, Multimodal & Training)",
        3: "Tier 3: Unified 3-in-1 Super Engine (llama.cpp + PyTorch + AirEngine)"
    }

    return {
        "status": "started",
        "pid": proc.pid,
        "port": port,
        "host": host,
        "tier": engine_tier,
        "tier_name": tier_names.get(engine_tier, "Unified Super Engine"),
        "forever": forever,
        "initiator": initiator,
        "healthy": healthy,
        "log_file": SERVER_LOG,
        "dashboard_url": f"http://localhost:{port}/dashboard",
        "api_url": f"http://{host}:{port}"
    }


def stop_server_daemon(force: bool = False, caller: str = "cli") -> Dict[str, Any]:
    """
    Gracefully terminates the background server process.
    If caller is 'cli' or 'gui' and the server is flagged forever=True (started via `lmms server start`),
    it will keep the daemon alive unless force=True.
    """
    pid = is_server_running()
    if not pid:
        # Clean up stale metadata if any
        for path in (PID_FILE, META_FILE):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        return {"status": "not_running"}

    meta = get_server_metadata()
    if not force and caller in ["cli", "gui"] and meta.get("forever") is True:
        return {
            "status": "kept_alive",
            "pid": pid,
            "reason": "Server was launched via 'lmms server start' (permanent background daemon)"
        }

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(25):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            # Force kill if still lingering
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    except OSError:
        pass

    for path in (PID_FILE, META_FILE):
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    return {"status": "stopped", "pid": pid}


def get_server_daemon_status() -> Dict[str, Any]:
    """Returns active runtime server status with tier and lifetime metadata."""
    pid = is_server_running()
    running = pid is not None
    meta = get_server_metadata() if running else {}

    recent_logs = []
    if os.path.exists(SERVER_LOG):
        try:
            with open(SERVER_LOG, "r") as f:
                lines = f.readlines()
                recent_logs = [l.strip() for l in lines[-10:] if l.strip()]
        except Exception:
            pass

    tier_val = meta.get("tier", 3)
    tier_names = {
        1: "Tier 1 (llama.cpp + AirEngine)",
        2: "Tier 2 (PyTorch + AirEngine)",
        3: "Tier 3 (Unified 3-in-1 Super Engine: llama.cpp + PyTorch + AirEngine)"
    }

    return {
        "running": running,
        "pid": pid,
        "port": meta.get("port", 11435),
        "host": meta.get("host", "0.0.0.0"),
        "tier": tier_val,
        "tier_name": tier_names.get(tier_val, "Tier 3 (Unified Super Engine)"),
        "forever": meta.get("forever", False),
        "initiator": meta.get("initiator", "unknown"),
        "started_at": meta.get("started_at"),
        "log_file": SERVER_LOG,
        "recent_logs": recent_logs
    }
