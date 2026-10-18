"""
PromptCache: Manages prompt prefix stability to maximize KV cache reuse in local engines.
Ensures base instructions and selected tool definitions remain canonical.
Only records real cache hits backed by actual backend engine telemetry.
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class PrefixCacheState:
    model_name: str
    prefix_hash: str
    prefix_length_chars: int
    tool_ids: tuple
    created_at: float
    last_hit_at: float = 0.0
    hit_count: int = 0
    is_reusable: bool = True


class PromptCacheManager:
    """
    Tracks and optimizes prompt prefix compatibility for llama.cpp / vLLM / PyTorch KV caches.
    """

    def __init__(self):
        self._current_cache: Optional[PrefixCacheState] = None
        self._cache_history: Dict[str, PrefixCacheState] = {}
        self._total_hits = 0
        self._total_misses = 0

    def compute_prefix_hash(self, base_system_prompt: str, tool_schemas_str: str) -> str:
        """Computes a deterministic hash of the static prompt prefix."""
        combined = f"{base_system_prompt.strip()}\n---\n{tool_schemas_str.strip()}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def check_prefix_compatibility(
        self,
        model_name: str,
        base_system_prompt: str,
        tool_schemas_str: str,
        selected_tool_ids: list
    ) -> bool:
        """
        Checks if the assembled prompt prefix matches the active KV cache prefix.
        """
        prefix_hash = self.compute_prefix_hash(base_system_prompt, tool_schemas_str)
        canonical_tools = tuple(sorted(selected_tool_ids))

        if (
            self._current_cache
            and self._current_cache.model_name == model_name
            and self._current_cache.prefix_hash == prefix_hash
            and self._current_cache.tool_ids == canonical_tools
        ):
            return True

        # New or changed prefix
        self._current_cache = PrefixCacheState(
            model_name=model_name,
            prefix_hash=prefix_hash,
            prefix_length_chars=len(base_system_prompt) + len(tool_schemas_str),
            tool_ids=canonical_tools,
            created_at=time.time()
        )
        self._cache_history[prefix_hash] = self._current_cache
        return False

    def record_engine_telemetry(self, model_name: str, prefix_hash: str, engine_reported_cache_hit: bool):
        """
        Only increments real cache hit count if engine telemetry explicitly verified it.
        """
        if engine_reported_cache_hit:
            self._total_hits += 1
            if self._current_cache and self._current_cache.prefix_hash == prefix_hash:
                self._current_cache.hit_count += 1
                self._current_cache.last_hit_at = time.time()
        else:
            self._total_misses += 1

    def invalidate(self, reason: str = "model or context switch"):
        """Invalidates active cache state."""
        self._current_cache = None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_ratio": (self._total_hits / max(1, self._total_hits + self._total_misses)),
            "active_prefix_hash": self._current_cache.prefix_hash if self._current_cache else None,
            "active_model": self._current_cache.model_name if self._current_cache else None
        }
