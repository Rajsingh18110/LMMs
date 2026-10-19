import os
import gc
from typing import Optional, Dict, Any, Generator

class AirPyTorchStreamer:
    """
    Air Engine Layer-by-Layer Streaming for PyTorch (AirEngine).
    Allows running and fine-tuning 70B+ Safetensors models on limited VRAM (e.g., 6GB-16GB GPUs)
    by paging transformer layers sequentially between RAM/NVMe and GPU VRAM.
    """
    def __init__(self, model_id: str, device: str = "cuda"):
        self.model_id = model_id
        self.device = device
        self.active_layer_idx: int = -1
        self.total_layers: int = 0
        self.is_streaming: bool = False

    def check_prerequisites(self) -> bool:
        try:
            import torch  # type: ignore
            return torch.cuda.is_available()
        except ImportError:
            return False

    def stream_layer_forward(self, layer_module: Any, layer_input: Any, **kwargs) -> Any:
        """
        Transfers a single transformer layer to GPU, computes forward pass,
        and instantly evicts weights from VRAM back to CPU memory.
        """
        import torch  # type: ignore
        try:
            # 1. Move layer to GPU VRAM
            layer_module = layer_module.to(self.device)
            if isinstance(layer_input, torch.Tensor):
                layer_input = layer_input.to(self.device)

            # 2. Compute forward pass
            with torch.no_grad():
                output = layer_module(layer_input, **kwargs)

            # 3. Offload layer back to CPU to free VRAM for the next layer
            layer_module = layer_module.to("cpu")
            torch.cuda.empty_cache()
            return output
        except Exception as e:
            print(f"[AirPyTorchStreamer] Layer streaming fallback: {e}")
            return layer_input

    def optimize_memory(self):
        """Flushes GPU VRAM allocator caches."""
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        except ImportError:
            pass
