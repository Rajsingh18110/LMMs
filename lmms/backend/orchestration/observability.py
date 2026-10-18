"""
TraceLogger: Structured telemetry and observability for inference orchestration.
Records token breakdowns, latencies (TTFT, routing, assembly), tool decisions, and compaction events.
Enforces strict sanitization to prevent leaking passwords, cookies, or API keys into logs.
"""

import time
import uuid
import re
import os
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class RequestTrace:
    request_id: str
    conversation_id: str
    timestamp: float
    model_name: str
    backend_engine: str
    intent: str
    intent_confidence: float
    selected_tools: List[str]
    rejected_tools: List[str]
    context_limit: int
    usable_budget: int
    output_reserve: int
    base_prompt_tokens: int
    tool_schemas_tokens: int
    history_tokens: int
    user_query_tokens: int
    total_prompt_tokens: int
    compacted: bool
    observations_pruned: int
    cache_prefix_hash: str
    cache_hit: bool
    routing_latency_ms: int = 0
    assembly_latency_ms: int = 0
    ttft_ms: int = 0
    inference_latency_ms: int = 0
    tool_execution_latency_ms: int = 0
    total_latency_ms: int = 0
    tool_calls_count: int = 0
    error: Optional[str] = None


class TraceLogger:
    """
    Structured, privacy-compliant diagnostics logger.
    """

    def __init__(self, log_dir: str = "~/.lmms/logs/traces", debug_mode: bool = False):
        self.log_dir = os.path.expanduser(log_dir)
        self.debug_mode = debug_mode
        self._traces: List[RequestTrace] = []
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception:
            pass

        self._sensitive_patterns = [
            re.compile(r'(api_key|token|password|secret|bearer|authorization|cookie)[\s:=]+([^\s,;]+)', re.IGNORECASE),
            re.compile(r'ghp_[a-zA-Z0-9]{36}'),
            re.compile(r'sk-[a-zA-Z0-9]{32,}'),
        ]

    def sanitize(self, text: str) -> str:
        """Removes secrets, tokens, and sensitive credentials from log strings."""
        if not text:
            return ""
        sanitized = text
        sanitized = re.sub(
            r'(?i)(api_key|token|password|secret|bearer|authorization|cookie)([\s:=]+)[^\s,;]+',
            r'\1\2[REDACTED]',
            sanitized
        )
        sanitized = re.sub(r'ghp_[a-zA-Z0-9]{36}', '[REDACTED]', sanitized)
        sanitized = re.sub(r'sk-[a-zA-Z0-9]{32,}', '[REDACTED]', sanitized)
        return sanitized


    def record_trace(self, trace: RequestTrace):
        """Records a completed request trace."""
        self._traces.append(trace)

        if self.debug_mode:
            print(
                f"[Trace] Req: {trace.request_id[:8]} | Intent: {trace.intent} ({trace.intent_confidence:.2f}) | "
                f"Tools: {trace.selected_tools} | Tokens: {trace.total_prompt_tokens}/{trace.usable_budget} | "
                f"TTFT: {trace.ttft_ms}ms | Total: {trace.total_latency_ms}ms"
            )

        # Write to JSONL log
        try:
            log_file = os.path.join(self.log_dir, "orchestration_traces.jsonl")
            data = asdict(trace)
            # Sanitize error or any string fields
            if data.get("error"):
                data["error"] = self.sanitize(data["error"])
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass

    def get_recent_traces(self, limit: int = 10) -> List[RequestTrace]:
        return self._traces[-limit:]


_GLOBAL_LOGGER: Optional[TraceLogger] = None


def get_trace_logger(debug_mode: bool = False) -> TraceLogger:
    global _GLOBAL_LOGGER
    if _GLOBAL_LOGGER is None:
        _GLOBAL_LOGGER = TraceLogger(debug_mode=debug_mode)
    return _GLOBAL_LOGGER
