"""
LMMs CLI Engine - Standalone HTTP Client
Communicates with local or remote LMMs Engines over Wi-Fi / LAN or localhost.
Zero hard dependencies on GPU/Torch/GUI modules.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Generator

from lmms.cli.remote import RemoteManager


class CLIClient:
    """Lightweight, resilient API client for local and remote LMMs engines."""

    def __init__(self, base_url: Optional[str] = None):
        self.remote_mgr = RemoteManager()
        self.base_url = (base_url or self.remote_mgr.get_active_url()).rstrip("/")

    def refresh_url(self) -> str:
        """Reload active URL from RemoteManager."""
        self.base_url = self.remote_mgr.get_active_url().rstrip("/")
        return self.base_url

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Perform a standard JSON HTTP request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "lmms-cli/1.0"
        }
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8")
                return json.loads(content) if content else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(err_body)
                msg = parsed.get("detail", err_body)
            except Exception:
                msg = err_body
            raise RuntimeError(f"Engine HTTP {e.code}: {msg}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Cannot connect to engine at {self.base_url}: {e.reason}") from e

    def get_health(self) -> Dict[str, Any]:
        """Check engine health and loaded models."""
        return self._request("/webhook", timeout=3.0)

    def get_stats(self) -> Dict[str, Any]:
        """Query engine hardware profiler and memory metrics."""
        return self._request("/v1/air/stats", timeout=5.0)

    def get_ps(self) -> List[Dict[str, Any]]:
        """Query running / active models from engine."""
        try:
            res = self._request("/v1/air/ps", timeout=5.0)
            if isinstance(res, list):
                return res
        except Exception:
            pass
        # Fallback to models/ps
        try:
            res = self._request("/v1/models/ps", timeout=5.0)
            return res if isinstance(res, list) else []
        except Exception:
            return []

    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models on the engine."""
        try:
            res = self._request("/v1/models/list", timeout=5.0)
            if isinstance(res, list):
                return res
            elif isinstance(res, dict) and "models" in res:
                return res["models"]
        except Exception:
            pass
        # Fallback to cache inventory
        try:
            cache = self._request("/v1/air/cache", timeout=5.0)
            models = []
            for m in cache.get("vram_models", []):
                models.append({"name": m, "location": "VRAM", "active": True})
            for m in cache.get("ram_models", []):
                models.append({"name": m, "location": "RAM Cache", "active": False})
            for m in cache.get("disk_models", []):
                models.append({"name": m, "location": "Disk", "active": False})
            return models
        except Exception:
            return []

    def get_info(self, model_name: str) -> Dict[str, Any]:
        """Retrieve model metadata."""
        return self._request(f"/v1/models/info/{model_name}", timeout=5.0)

    def load_model(self, model_name: str, model_path: Optional[str] = None) -> Dict[str, Any]:
        """Request engine to load a model."""
        return self._request("/v1/models/load", method="POST", data={
            "model_name": model_name,
            "model_path": model_path
        }, timeout=60.0)

    def unload_model(self, model_name: str) -> Dict[str, Any]:
        """Request engine to unload a model."""
        return self._request("/v1/models/unload", method="POST", data={
            "model_name": model_name
        }, timeout=15.0)

    def stream_chat(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        mode: str = "deep",
        think: bool = True,
        timeout: float = 120.0
    ) -> Generator[str, None, None]:
        """
        Stream tokens from /v1/chat/completions over HTTP Server-Sent Events (SSE).
        Yields raw text content chunks in real-time.
        """
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "lmms-cli/1.0"
        }
        payload = {
            "model_name": model_name,
            "messages": messages,
            "stream": True,
            "mode": mode,
            "think": think
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for line in resp:
                    decoded = line.decode("utf-8").strip()
                    if not decoded:
                        continue
                    if decoded.startswith("data: "):
                        raw_data = decoded[6:].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw_data)
                            if "error" in chunk:
                                raise RuntimeError(f"Engine Error: {chunk['error']}")
                            content = chunk.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Chat stream error (HTTP {e.code}): {err}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Connection lost to engine {self.base_url}: {e.reason}") from e
