import os
import threading
from typing import Optional
from lmms.engine.air.memory_map import GGUFMemoryMap

class AirLayerPrefetcher:
    """
    Double-buffered asynchronous layer streaming pipeline for Regime 3 (AirLLM-Style).
    Prefetches layer (l+1) via kernel readahead while layer (l) forward pass computes.
    Evicts layer (l-1) immediately via posix_fadvise(DONTNEED) to eliminate OS page cache thrashing.
    """
    def __init__(self, mmap_engine: GGUFMemoryMap, total_layers: int):
        self.mmap_engine = mmap_engine
        self.total_layers = total_layers
        self.current_layer = 0
        self.active_buffer = 0  # 0 or 1 (ping-pong)
        self._lock = threading.Lock()

    def advance_to_layer(self, layer_idx: int):
        """
        Signals forward step at layer_idx.
        - Triggers asynchronous readahead on layer (l+1).
        - Discards memory footprint of layer (l-1) from page cache.
        """
        with self._lock:
            self.current_layer = layer_idx
            self.active_buffer = layer_idx % 2
            
            # 1. Prefetch upcoming layer
            if layer_idx + 1 < self.total_layers:
                self.mmap_engine.prefetch_layer(layer_idx + 1, self.total_layers)
                
            # 2. Evict previous layer from kernel page cache
            if layer_idx > 0:
                self.mmap_engine.evict_layer(layer_idx - 1, self.total_layers)

    def reset(self):
        with self._lock:
            self.current_layer = 0
            self.active_buffer = 0
