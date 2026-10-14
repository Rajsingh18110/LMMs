"""
Engine 1: Universal PyTorch Runtime
Handles full-precision and quantized models via PyTorch and HuggingFace Transformers.
"""
from lmms.engine.runtimes.universal_pytorch import UniversalPyTorchRuntime

__all__ = ["UniversalPyTorchRuntime"]
