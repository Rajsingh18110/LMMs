"""
LMMs Daemon Service Controller
Manages background and daemon lifecycle for the LMMs API Server.
"""

from __future__ import annotations

import os
import sys
import time
import signal
import subprocess
from typing import Dict, Any, Optional

LMMS_HOME = os.path.expanduser("~/.lmms")
PID_FILE = os.path.join(LMMS_HOME, "server.pid")
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
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        return None


def get_ai_python_executable() -> str:
    """Finds the Python interpreter that has AI engine dependencies (llama_cpp, torch) installed."""
    venv_py = os.path.expanduser("~/.lmms/app/venv/bin/python")
    if os.path.exists(venv_py):
        return venv_py

    try:
        import llama_cpp
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


def start_server_daemon(port: int = 11435, host: str = "0.0.0.0", engine_mode: str = "auto") -> Dict[str, Any]:
    """Starts the LMMs API Server as a detached background process."""
    _ensure_dirs()
    existing_pid = is_server_running()
    if existing_pid:
        return {
            "status": "already_running",
            "pid": existing_pid,
            "port": port,
            "host": host,
            "url": f"http://{host}:{port}"
        }

    env = os.environ.copy()
    if engine_mode:
        env["LMMS_ENGINE_MODE"] = engine_mode

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    curr_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{curr_pp}" if curr_pp else project_root

    python_exe = get_ai_python_executable()

    # Run `python -m lmms.api.server` in background detached
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

    # Give server a brief moment to boot
    time.sleep(0.5)

    return {
        "status": "started",
        "pid": proc.pid,
        "port": port,
        "host": host,
        "log_file": SERVER_LOG,
        "dashboard_url": f"http://localhost:{port}/dashboard",
        "api_url": f"http://{host}:{port}"
    }


def stop_server_daemon() -> Dict[str, Any]:
    """Gracefully terminates the background server process."""
    pid = is_server_running()
    if not pid:
        return {"status": "not_running"}

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
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

    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    return {"status": "stopped", "pid": pid}


def get_server_daemon_status() -> Dict[str, Any]:
    """Returns active runtime server status."""
    pid = is_server_running()
    running = pid is not None

    recent_logs = []
    if os.path.exists(SERVER_LOG):
        try:
            with open(SERVER_LOG, "r") as f:
                lines = f.readlines()
                recent_logs = [l.strip() for l in lines[-10:] if l.strip()]
        except Exception:
            pass

    return {
        "running": running,
        "pid": pid,
        "log_file": SERVER_LOG,
        "recent_logs": recent_logs
    }
