"""Runtime Cache Manager implementing CacheContract.

Provides thread-safe session KV caching, generation state caching,
and hardware memory tracking for LMMs backend.
"""

from __future__ import annotations

import collections
import gc
import logging
import psutil
import threading
import time
from typing import Any, Dict, Optional

from lmms.backend.contracts.cache import CacheContract

logger = logging.getLogger("lmms.runtime.cache_manager")


class CacheItem:
    def __init__(self, key: str, value: Any, ttl: Optional[float] = None):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.time() - self.last_accessed) > self.ttl

    def access(self) -> Any:
        self.last_accessed = time.time()
        return self.value


class CacheManager(CacheContract):
    """Production CacheManager fulfilling CacheContract with LRU and TTL support."""

    _instance: Optional["CacheManager"] = None
    _lock = threading.Lock()

    def __init__(self, max_items: int = 500, default_ttl: Optional[float] = 3600.0):
        self.max_items = max_items
        self.default_ttl = default_ttl
        self._cache: collections.OrderedDict[str, CacheItem] = collections.OrderedDict()
        self._cache_lock = threading.Lock()
        self.loaded_models: Dict[str, float] = {}

    @classmethod
    def get_instance(cls, max_items: int = 500, default_ttl: Optional[float] = 3600.0) -> "CacheManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(max_items=max_items, default_ttl=default_ttl)
            return cls._instance

    # -------------------------------------------------------------
    # CacheContract Implementation
    # -------------------------------------------------------------

    def get_cache(self, session_id: str) -> Any:
        """Retrieve cached state or KV cache for session_id."""
        with self._cache_lock:
            item = self._cache.get(session_id)
            if not item:
                return None
            if item.is_expired():
                del self._cache[session_id]
                return None
            # Move to end for LRU
            self._cache.move_to_end(session_id)
            return item.access()

    def set_cache(self, session_id: str, cache_state: Any, ttl: Optional[float] = None) -> bool:
        """Store cache state for session_id."""
        with self._cache_lock:
            if session_id in self._cache:
                self._cache.move_to_end(session_id)

            effective_ttl = ttl if ttl is not None else self.default_ttl
            self._cache[session_id] = CacheItem(session_id, cache_state, effective_ttl)

            # Evict oldest if capacity exceeded
            while len(self._cache) > self.max_items:
                oldest_key, _ = self._cache.popitem(last=False)
                logger.debug("Evicted oldest cache item: %s", oldest_key)

            return True

    def clear_cache(self, session_id: str) -> bool:
        """Clear cache state for a single session_id."""
        with self._cache_lock:
            if session_id in self._cache:
                del self._cache[session_id]
                return True
            return False

    def clear_all(self) -> None:
        """Clear all cached sessions and states."""
        with self._cache_lock:
            self._cache.clear()
        gc.collect()

    # -------------------------------------------------------------
    # Engine Compatibility & Hardware Stats
    # -------------------------------------------------------------

    def location(self, model_id: str) -> str:
        return "VRAM" if model_id in self.loaded_models else "DISK"

    def put_vram(self, model_id: str, size_gb: float = 0.0) -> None:
        self.loaded_models[str(model_id)] = float(size_gb)

    def evict_vram(self, model_id: Optional[str] = None) -> Optional[str]:
        if model_id and model_id in self.loaded_models:
            del self.loaded_models[model_id]
            gc.collect()
            return model_id
        elif self.loaded_models:
            first_key = next(iter(self.loaded_models))
            del self.loaded_models[first_key]
            gc.collect()
            return first_key
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics and loaded models."""
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024**3)
        available_gb = mem.available / (1024**3)
        used_gb = total_gb - available_gb

        return {
            "device": "CPU",
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "available_gb": round(available_gb, 2),
            "loaded_models": list(self.loaded_models.keys()),
            "cached_sessions": len(self._cache),
        }


# Aliases for backward compatibility
RuntimeCacheManager = CacheManager

__all__ = ["CacheManager", "RuntimeCacheManager", "CacheItem"]
