"""
lmms.backend.telemetry.metrics - Execution metrics, token counting, and latency tracking.
Persists cumulative and per-session runtime telemetry to ~/.lmms/telemetry/metrics.json.
"""

from __future__ import annotations

import os
import json
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class ToolMetrics:
    invocations: int = 0
    successes: int = 0
    failures: int = 0
    total_duration_s: float = 0.0

    @property
    def avg_duration_s(self) -> float:
        return self.total_duration_s / self.invocations if self.invocations > 0 else 0.0


@dataclass
class SessionMetrics:
    session_id: str
    start_time: float = field(default_factory=time.time)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_requests: int = 0
    total_llm_duration_s: float = 0.0
    tool_metrics: Dict[str, ToolMetrics] = field(default_factory=dict)
    errors_count: int = 0


class MetricsTracker:
    """Thread-safe persistent runtime metrics collector."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.expanduser("~/.lmms/telemetry/metrics.json")
        self._lock = threading.Lock()
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0
        self.total_duration_s = 0.0
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.active_session_id: Optional[str] = None

        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.total_prompt_tokens = data.get("total_prompt_tokens", 0)
                self.total_completion_tokens = data.get("total_completion_tokens", 0)
                self.total_requests = data.get("total_requests", 0)
                self.total_duration_s = data.get("total_duration_s", 0.0)
                self.tools = data.get("tools", {})
            except Exception:
                pass

    def _save(self):
        try:
            data = {
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
                "total_requests": self.total_requests,
                "total_duration_s": self.total_duration_s,
                "tools": self.tools,
                "last_updated": time.time(),
            }
            tmp_path = self.storage_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.storage_path)
        except Exception:
            pass

    def record_tokens(self, prompt_tokens: int, completion_tokens: int, duration_s: float = 0.0):
        with self._lock:
            self.total_prompt_tokens += max(0, prompt_tokens)
            self.total_completion_tokens += max(0, completion_tokens)
            self.total_requests += 1
            self.total_duration_s += max(0.0, duration_s)
            self._save()

    def record_tool_call(self, tool_name: str, duration_s: float, success: bool):
        with self._lock:
            if tool_name not in self.tools:
                self.tools[tool_name] = {
                    "invocations": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_duration_s": 0.0
                }
            entry = self.tools[tool_name]
            entry["invocations"] += 1
            if success:
                entry["successes"] += 1
            else:
                entry["failures"] += 1
            entry["total_duration_s"] += max(0.0, duration_s)
            self._save()

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "total_requests": self.total_requests,
                "total_duration_s": round(self.total_duration_s, 3),
                "avg_request_duration_s": round(self.total_duration_s / self.total_requests, 3) if self.total_requests > 0 else 0.0,
                "tools_used": len(self.tools),
                "tools_summary": dict(self.tools)
            }


default_metrics = MetricsTracker()
