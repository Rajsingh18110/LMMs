"""
Engine 2: LlamaCpp High-Throughput Runtime
Handles GGUF quantized models with C++ tensor acceleration.
"""
from lmms.engine.runtimes.llama_cpp import LlamaCppRuntime

__all__ = ["LlamaCppRuntime"]
