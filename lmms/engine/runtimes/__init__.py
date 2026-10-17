from .base import RuntimeContract

def __getattr__(name: str):
    if name == "UniversalPyTorchRuntime":
        from .engine_1_pytorch import UniversalPyTorchRuntime
        return UniversalPyTorchRuntime
    elif name == "LlamaCppRuntime":
        from .engine_2_llamacpp import LlamaCppRuntime
        return LlamaCppRuntime
    elif name == "AirRuntime":
        from .engine_3_air import AirRuntime
        return AirRuntime
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "RuntimeContract",
    "UniversalPyTorchRuntime",
    "LlamaCppRuntime",
    "AirRuntime",
]
