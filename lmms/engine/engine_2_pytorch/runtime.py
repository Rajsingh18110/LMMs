import os
import time
from typing import Any, Dict, List, Optional
from lmms.engine.core.base import RuntimeContract
from lmms.engine.engine_2_pytorch.air_streamer import AirPyTorchStreamer
from lmms.engine.engine_2_pytorch.trainer import AirTrainer
from lmms.engine.runtimes.universal_pytorch import UniversalPyTorchRuntime

class AirPyTorchRuntime(RuntimeContract):
    """
    Engine 2: Air Engine + PyTorch Enterprise Runtime.
    - HuggingFace Safetensors & Multimodal (Vision, Audio, TTS) execution.
    - AirEngine layer-by-layer sequential offload for heavy 70B+ models on limited VRAM.
    - LoRA / PEFT fine-tuning and training offloader.
    """
    def __init__(self):
        self._universal = UniversalPyTorchRuntime()
        self.streamer: Optional[AirPyTorchStreamer] = None
        self.trainer: Optional[AirTrainer] = None
        self.active_model_id: Optional[str] = None
        self._is_loaded = False

    @property
    def _models(self) -> Dict[str, Any]:
        """Dictionary of currently loaded active models."""
        if self._is_loaded and self.active_model_id:
            return {self.active_model_id: getattr(self._universal, "model", None)}
        return {}

    @property
    def _model_id(self) -> str:
        return self.active_model_id or ""

    def load_model(self, model_id: str) -> bool:
        self.streamer = AirPyTorchStreamer(model_id)
        self.trainer = AirTrainer(model_id)
        success = self._universal.load_model(model_id)
        if success:
            self.active_model_id = model_id
            self._is_loaded = True
        return success

    def unload_model(self, model_id: Optional[str] = None) -> bool:
        if hasattr(self._universal, "unload_model"):
            getattr(self._universal, "unload_model")(model_id or "")
        else:
            setattr(self._universal, "model", None)
            setattr(self._universal, "tokenizer", None)
            setattr(self._universal, "pipe", None)
            setattr(self._universal, "_is_loaded", False)
        self.active_model_id = None
        self._is_loaded = False
        if self.streamer:
            self.streamer.optimize_memory()
        return True

    def chat(self, model: str, messages: list, stream: bool = False, options: Optional[dict] = None, **kwargs) -> Any:
        context = {
            'messages': messages,
            'model_name': model,
            'model_id': model
        }
        return self.generate(context, stream)

    def generate(self, context: Any, stream: bool = False) -> Any:
        return self._universal.generate(context, stream)

    def embed(self, text: str) -> List[float]:
        if hasattr(self._universal, "embed"):
            return getattr(self._universal, "embed")(text)
        return [0.0]

    def tokenize(self, text: str) -> List[int]:
        if hasattr(self._universal, "tokenize"):
            return getattr(self._universal, "tokenize")(text)
        tokenizer = getattr(self._universal, "tokenizer", None)
        if tokenizer and hasattr(tokenizer, "encode"):
            return list(tokenizer.encode(text))
        return []

    def health(self) -> Dict[str, Any]:
        return {
            "engine": "Engine 2: Air + PyTorch Enterprise",
            "active_model": self.active_model_id,
            "is_loaded": self._is_loaded,
            "pipeline_tag": getattr(self._universal, "pipeline_tag", "text-generation"),
            "training_ready": self.trainer.is_available() if self.trainer else False
        }
