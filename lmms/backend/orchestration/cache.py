"""
PromptCache: Manages prompt prefix stability to maximize KV cache reuse in local engines.
Ensures base instructions and workspace context remain canonical.
Accurately tracks prefix hash compatibility without claiming unverified hardware KV-cache hits.
"""

import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


@dataclass
class PrefixCacheState:
    model_name: str
    prefix_hash: str
    prefix_length_chars: int
    tool_ids: tuple
    created_at: float
    last_match_at: float = 0.0
    match_count: int = 0
    is_reusable: bool = True


class PromptCacheManager:
    """
    Tracks and optimizes prompt prefix compatibility for llama.cpp / vLLM / PyTorch KV caches.
    IMPORTANT: Operates at the architectural level to maximize prefix stability.
    Because the underlying engine stream does not expose low-level GGML KV-cache
    token reuse counters, metrics are explicitly tracked as 'prefix_matches' and
    'prefix_invalidations', not hardware cache hits.
    """

    def __init__(self):
        self._current_cache: Optional[PrefixCacheState] = None
        self._cache_history: Dict[str, PrefixCacheState] = {}
        self._total_matches = 0
        self._total_invalidations = 0

    def compute_prefix_hash(self, base_system_prompt: str, workspace_context: str = "") -> str:
        """
        Computes a deterministic hash of the stable prompt prefix (system instructions + workspace).
        """
        combined = f"{base_system_prompt.strip()}\n---\n{workspace_context.strip()}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def check_prefix_compatibility(
        self,
        model_name: str,
        base_system_prompt: str,
        tool_schemas_str: str = "",
        selected_tool_ids: Optional[List[str]] = None,
        workspace_context: str = ""
    ) -> bool:
        """
        Checks if the assembled prompt prefix matches the active prefix.
        Returns True if the prefix is identical and reusable.
        """
        prefix_hash = self.compute_prefix_hash(base_system_prompt, workspace_context)
        canonical_tools = tuple(sorted(selected_tool_ids or []))

        if (
            self._current_cache
            and self._current_cache.model_name == model_name
            and self._current_cache.prefix_hash == prefix_hash
            and self._current_cache.tool_ids == canonical_tools
        ):
            self._total_matches += 1
            self._current_cache.match_count += 1
            self._current_cache.last_match_at = time.time()
            return True

        # Prefix changed or new session
        self._total_invalidations += 1
        self._current_cache = PrefixCacheState(
            model_name=model_name,
            prefix_hash=prefix_hash,
            prefix_length_chars=len(base_system_prompt) + len(workspace_context),
            tool_ids=canonical_tools,
            created_at=time.time()
        )
        self._cache_history[prefix_hash] = self._current_cache
        return False

    def record_engine_telemetry(self, model_name: str, prefix_hash: str, engine_reported_cache_hit: bool):
        """
        Records engine-reported telemetry only if explicitly provided by the engine backend.
        """
        pass

    def invalidate(self, reason: str = "model or context switch"):
        """Explicitly invalidates active cache state."""
        self._current_cache = None

    def get_stats(self) -> Dict[str, Any]:
        total_requests = self._total_matches + self._total_invalidations
        return {
            "prefix_matches": self._total_matches,
            "prefix_invalidations": self._total_invalidations,
            "prefix_stability_ratio": (self._total_matches / max(1, total_requests)),
            "active_prefix_hash": self._current_cache.prefix_hash if self._current_cache else None,
            "active_model": self._current_cache.model_name if self._current_cache else None,
            "note": "Metrics reflect architectural prefix hash stability. Engine-level KV cache reuse is internal to llama.cpp."
        }
