"""
LMMs CLI Engine - Wi-Fi / LAN Remote Connection & Discovery Manager
Manages remote engine endpoints, network auto-discovery, latency telemetry,
and configuration persistence.
"""

from __future__ import annotations

import json
import os
import queue
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple, Any

# ANSI Typography Tokens
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_DIM_GREY = "\033[90m"
COLOR_CYAN = "\033[36m"
COLOR_BOLD_CYAN = "\033[1;36m"
COLOR_GREEN = "\033[32m"
COLOR_BOLD_GREEN = "\033[1;32m"
COLOR_BOLD_WHITE = "\033[1;37m"
COLOR_RED = "\033[31m"
COLOR_YELLOW = "\033[33m"

CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"

CONFIG_DIR = os.path.expanduser("~/.lmms")
REMOTE_CONFIG_FILE = os.path.join(CONFIG_DIR, "remote_config.json")
DEFAULT_PORT = 11435


class RemoteManager:
    """Manages local and remote engine connections across Wi-Fi / LAN."""

    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(REMOTE_CONFIG_FILE):
            try:
                with open(REMOTE_CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "mode": "local",  # "local" or "remote"
            "active_remote": None,
            "remotes": {}
        }

    def _save_config(self) -> None:
        try:
            with open(REMOTE_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to persist remote config: {e}\n")

    def get_active_url(self) -> str:
        """Return the base URL for the active engine (local or remote)."""
        mode = self.config.get("mode", "local")
        if mode == "remote":
            active_name = self.config.get("active_remote")
            remotes = self.config.get("remotes", {})
            if active_name and active_name in remotes:
                return remotes[active_name].get("url", f"http://127.0.0.1:{DEFAULT_PORT}")
        return f"http://127.0.0.1:{DEFAULT_PORT}"

    def get_active_info(self) -> Dict[str, Any]:
        """Return detailed information on current active target."""
        mode = self.config.get("mode", "local")
        if mode == "remote":
            active_name = self.config.get("active_remote")
            remotes = self.config.get("remotes", {})
            if active_name and active_name in remotes:
                info = dict(remotes[active_name])
                info["mode"] = "remote"
                info["name"] = active_name
                return info
        return {
            "mode": "local",
            "name": "localhost",
            "host": "127.0.0.1",
            "port": DEFAULT_PORT,
            "url": f"http://127.0.0.1:{DEFAULT_PORT}"
        }

    def ping(self, url: str, timeout: float = 1.5) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Check health and measure round-trip latency to an engine endpoint.
        Returns: (is_online, latency_ms, payload)
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        target = f"{url.rstrip('/')}/webhook"
        
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(target, headers={"User-Agent": "lmms-cli/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return True, round(elapsed_ms, 1), data
        except Exception:
            pass
        return False, 0.0, {}

    def set_local(self) -> None:
        """Switch active engine back to local host."""
        self.config["mode"] = "local"
        self._save_config()

    def set_remote(self, name_or_host: str, port: int = DEFAULT_PORT) -> Tuple[bool, str]:
        """
        Connect and set active remote engine.
        Accepts: '192.168.1.45', '192.168.1.45:11435', or saved remote name.
        """
        remotes = self.config.setdefault("remotes", {})

        # Check if it matches an existing saved remote name
        if name_or_host in remotes:
            target_url = remotes[name_or_host]["url"]
            name = name_or_host
        else:
            if ":" in name_or_host:
                parts = name_or_host.split(":")
                host = parts[0]
                port = int(parts[1])
            else:
                host = name_or_host
            target_url = f"http://{host}:{port}"
            name = host

        # Verify connection
        online, latency, data = self.ping(target_url)
        if not online:
            return False, f"Could not reach LMMs engine at {target_url} (timeout/connection refused)"

        remotes[name] = {
            "name": name,
            "url": target_url,
            "host": target_url.replace("http://", "").replace("https://", "").split(":")[0],
            "port": port,
            "last_seen": int(time.time()),
            "latency_ms": latency,
            "active_models": data.get("active_models", [])
        }
        self.config["mode"] = "remote"
        self.config["active_remote"] = name
        self._save_config()
        return True, f"Successfully connected to {name} ({latency}ms latency)"

    def remove_remote(self, name: str) -> bool:
        """Remove a saved remote from config."""
        remotes = self.config.get("remotes", {})
        if name in remotes:
            del remotes[name]
            if self.config.get("active_remote") == name:
                self.config["mode"] = "local"
                self.config["active_remote"] = None
            self._save_config()
            return True
        return False

    def list_remotes(self) -> List[Dict[str, Any]]:
        """Return list of all configured remotes with fresh latency probes."""
        remotes = self.config.get("remotes", {})
        results = []
        for name, info in remotes.items():
            item = dict(info)
            online, latency, data = self.ping(info["url"], timeout=1.0)
            item["online"] = online
            if online:
                item["latency_ms"] = latency
                item["active_models"] = data.get("active_models", [])
            results.append(item)
        return results

    @staticmethod
    def get_local_ip() -> str:
        """Discover the machine's primary LAN IP."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def scan_lan(self, port: int = DEFAULT_PORT) -> List[Dict[str, Any]]:
        """
        Scan Wi-Fi / LAN subnet concurrently with dynamic live progress
        to find all listening LMMs engines.
        """
        local_ip = self.get_local_ip()
        if local_ip.startswith("127."):
            prefix = "192.168.1."
        else:
            prefix = ".".join(local_ip.split(".")[:3]) + "."

        candidates = [f"{prefix}{i}" for i in range(1, 255)]
        # Always include localhost
        if "127.0.0.1" not in candidates:
            candidates.insert(0, "127.0.0.1")

        total_hosts = len(candidates)
        ip_queue: queue.Queue[str] = queue.Queue()
        for ip in candidates:
            ip_queue.put(ip)

        found: List[Dict[str, Any]] = []
        found_lock = threading.Lock()
        scanned_count = [0]
        count_lock = threading.Lock()

        def scan_worker():
            while not ip_queue.empty():
                try:
                    ip = ip_queue.get_nowait()
                except queue.Empty:
                    break

                # Quick socket connect probe (fast reject)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.25)
                try:
                    res = sock.connect_ex((ip, port))
                    sock.close()
                    if res == 0:
                        # Port open! Verify /webhook
                        url = f"http://ip:{port}".replace("ip", ip)
                        online, latency, data = self.ping(url, timeout=0.6)
                        if online:
                            with found_lock:
                                found.append({
                                    "host": ip,
                                    "port": port,
                                    "url": url,
                                    "latency_ms": latency,
                                    "active_models": data.get("active_models", []),
                                    "is_local": (ip in ["127.0.0.1", "localhost", local_ip])
                                })
                except Exception:
                    pass
                finally:
                    with count_lock:
                        scanned_count[0] += 1
                    ip_queue.task_done()

        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spin_idx = 0

        sys.stdout.write(CURSOR_HIDE)
        sys.stdout.write(
            f"🔍 {COLOR_BOLD_WHITE}LMMs LAN Discovery{COLOR_RESET} "
            f"{COLOR_DIM}(Subnet: {prefix}0/24 : {port}){COLOR_RESET}\n"
        )
        sys.stdout.flush()

        threads = []
        for _ in range(40):  # 40 concurrent discovery workers
            th = threading.Thread(target=scan_worker, daemon=True)
            th.start()
            threads.append(th)

        # Dynamic live spinner & 25-col linear progress bar
        while scanned_count[0] < total_hosts:
            pct = scanned_count[0] / total_hosts
            filled = int(pct * 25)
            bar = f"{COLOR_CYAN}{'━' * filled}{COLOR_DIM_GREY}{'─' * (25 - filled)}{COLOR_RESET}"
            sp = spinner[spin_idx % len(spinner)]
            spin_idx += 1

            sys.stdout.write(
                f"\r\033[K  {COLOR_BOLD_CYAN}{sp}{COLOR_RESET} "
                f"{COLOR_BOLD_WHITE}Scanning LAN{COLOR_RESET} "
                f"[{bar}] {COLOR_DIM}{int(pct * 100):>3}% ({len(found)} engine(s) found){COLOR_RESET}"
            )
            sys.stdout.flush()
            time.sleep(0.05)

        for th in threads:
            th.join(timeout=0.5)

        # Self-cleaning ephemeral wipe of the active progress line
        sys.stdout.write("\r\033[K")
        sys.stdout.write(CURSOR_SHOW)
        sys.stdout.flush()

        return found
