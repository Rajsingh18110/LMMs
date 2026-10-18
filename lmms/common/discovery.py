"""
LMMs Unified Engine Discovery & Multi-Tier Connection Resolver
Hierarchy: Localhost (127.0.0.1) -> LAN Auto-Discovery -> Global Remote URL -> Interactive Fallback
"""

from __future__ import annotations

import os
import sys
import json
import time
import socket
import threading
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

DEFAULT_ENGINE_PORT = 11435
DISCOVERY_BEACON_PORT = 11436
BEACON_MAGIC = b"LMMS_DISCOVERY_PING"
BEACON_REPLY_PREFIX = b"LMMS_DISCOVERY_PONG:"


def get_config_path() -> str:
    home_dir = os.path.expanduser("~/.lmms/config")
    os.makedirs(home_dir, exist_ok=True)
    return os.path.join(home_dir, "config.json")


def load_config() -> Dict[str, Any]:
    cfg_path = get_config_path()
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg: Dict[str, Any]) -> None:
    cfg_path = get_config_path()
    try:
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def is_engine_alive(url: str, timeout: float = 0.35) -> bool:
    """Fast probe to determine if an LMMs engine is actively serving HTTP on the URL."""
    clean_url = url.rstrip("/")
    probe_endpoints = [f"{clean_url}/ping", f"{clean_url}/v1/health", f"{clean_url}/health"]
    
    for ep in probe_endpoints:
        try:
            req = urllib.request.Request(
                ep,
                headers={"User-Agent": "LMMs-Discovery/2.5.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 204):
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError, OSError):
            continue
    return False


def get_local_ip() -> str:
    """Detects primary local LAN IP of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, purely for socket routing table resolution
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def discover_lan_engine(timeout: float = 0.8) -> Optional[str]:
    """
    Broadcasts UDP probe across the local subnet to detect any running LMMs Host Server.
    Returns 'http://<host>:<port>' if found, else None.
    """
    # 1. Quick check standard local hostnames
    for test_host in ["http://lmms-server.local:11435", "http://lmms-engine.local:11435", "http://lmms.local:11435"]:
        if is_engine_alive(test_host, timeout=0.25):
            return test_host

    # 2. UDP Broadcast Beacon Query
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    discovered_url = None
    try:
        sock.sendto(BEACON_MAGIC, ("<broadcast>", DISCOVERY_BEACON_PORT))
        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                if data.startswith(BEACON_REPLY_PREFIX):
                    payload = data[len(BEACON_REPLY_PREFIX):].decode("utf-8", errors="ignore")
                    # Format: port or host:port
                    if ":" in payload:
                        discovered_url = f"http://{payload}"
                    else:
                        discovered_url = f"http://{addr[0]}:{payload}"
                    
                    if is_engine_alive(discovered_url, timeout=0.3):
                        break
                    discovered_url = None
            except socket.timeout:
                break
    except Exception:
        pass
    finally:
        sock.close()

    return discovered_url


def start_lan_beacon(port: int = DEFAULT_ENGINE_PORT) -> threading.Thread:
    """
    Runs on the LMMs Server host: Listens for client discovery broadcast queries and replies.
    """
    def _beacon_loop():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", DISCOVERY_BEACON_PORT))
            while True:
                data, addr = sock.recvfrom(1024)
                if data == BEACON_MAGIC:
                    reply = BEACON_REPLY_PREFIX + str(port).encode("utf-8")
                    sock.sendto(reply, addr)
        except Exception:
            pass
        finally:
            sock.close()

    t = threading.Thread(target=_beacon_loop, daemon=True, name="LMMs-LAN-Beacon")
    t.start()
    return t


def save_engine_url(url: str) -> None:
    """Persists validated engine URL in user configuration."""
    cfg = load_config()
    cfg["engine_url"] = url.rstrip("/")
    cfg["last_resolved"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_config(cfg)


def get_engine_url(interactive: bool = True, force_check: bool = False) -> str:
    """
    Resolves the active LMMs Engine endpoint URL using prioritized hierarchy:
    1. Environment Variable 'LMMS_ENGINE_URL'
    2. Localhost Server (http://127.0.0.1:11435)
    3. Saved Config Remote Host (~/.lmms/config/config.json)
    4. LAN Auto-Discovery via UDP broadcast (lmms-engine on subnet)
    5. Global Fallback (Interactive terminal prompt or fallback to 127.0.0.1)
    """
    # Tier 1: Environment Override
    env_url = os.environ.get("LMMS_ENGINE_URL")
    if env_url:
        return env_url.rstrip("/")

    # Tier 2: Localhost Engine Check
    local_url = f"http://127.0.0.1:{DEFAULT_ENGINE_PORT}"
    if is_engine_alive(local_url, timeout=0.25):
        return local_url

    # Tier 3: Saved Configuration
    cfg = load_config()
    saved_url = cfg.get("engine_url")
    if saved_url and saved_url != local_url:
        if is_engine_alive(saved_url, timeout=0.6):
            return saved_url.rstrip("/")

    # Tier 4: LAN Auto-Discovery (Enterprise Host Node on office/home network)
    lan_url = discover_lan_engine(timeout=0.6)
    if lan_url:
        save_engine_url(lan_url)
        return lan_url

    # Tier 5: Fallback & Interactive Resolution
    if interactive and sys.stdin.isatty():
        print("\n\033[1;33m[LMMs Discovery]\033[0m No local LMMs engine is currently running.")
        print("\033[2mEnter Enterprise Server URL (e.g. http://192.168.1.50:11435 or https://ai.domain.com)\033[0m")
        try:
            user_input = input("\033[1;36mEnterprise Host URL\033[0m [Press Enter to start local engine]: ").strip()
            if user_input:
                if not user_input.startswith("http://") and not user_input.startswith("https://"):
                    user_input = f"http://{user_input}"
                if is_engine_alive(user_input, timeout=1.5):
                    print(f"\033[1;32m✔ Connected to Enterprise Host:\033[0m {user_input}")
                    save_engine_url(user_input)
                    return user_input.rstrip("/")
                else:
                    print(f"\033[1;33m⚠ Warning:\033[0m Host at {user_input} did not respond to ping. Using it anyway.")
                    save_engine_url(user_input)
                    return user_input.rstrip("/")
            else:
                # User pressed Enter: attempt to launch local daemon
                from lmms.api.service import start_server_daemon
                print("\033[1;34m> Spawning local LMMs engine daemon...\033[0m")
                start_server_daemon(port=DEFAULT_ENGINE_PORT, host="0.0.0.0")
                time.sleep(1.0)
                return local_url
        except (KeyboardInterrupt, EOFError):
            print("\n")
            return local_url

    # Default fallback
    return local_url
