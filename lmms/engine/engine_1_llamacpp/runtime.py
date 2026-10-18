import os
import time
from typing import Any, Dict, List, Optional
from lmms.engine.core.base import RuntimeContract
from lmms.engine.engine_1_llamacpp.scheduler import AirScheduler
from lmms.engine.engine_1_llamacpp.air_loader import AirLoader, ModelProfile
from lmms.engine.engine_1_llamacpp.air_pager import AirPager

class AirLlamaCppRuntime(RuntimeContract):
    """
    Engine 1: Air Engine + Llama.cpp High-Throughput Runtime.
    - Pure GPU acceleration when model fits in VRAM.
    - Dynamic Hybrid VRAM + DDR5 RAM offload (Tri-Regime) for heavy models.
    - Zero-latency mmap virtual memory allocation.
    - Quantized Q8_0 KV Cache + FlashAttention.
    """
    def __init__(self):
        self.scheduler = AirScheduler()
        self.pager = self.scheduler.pager
        self.loader = self.scheduler.loader
        self._is_loaded = True
        self.active_model_name: Optional[str] = None

    @property
    def _models(self) -> Dict[str, Any]:
        """Dictionary of currently loaded active models for backward compatibility."""
        models: Dict[str, Any] = {}
        if getattr(self, "pager", None) and self.pager.active_profile and self.pager.active_model:
            name = self.pager.active_profile.model_name
            clean_name = os.path.splitext(os.path.basename(name))[0]
            models[name] = self.pager.active_model
            models[clean_name] = self.pager.active_model
        elif self.active_model_name:
            clean_name = os.path.splitext(os.path.basename(self.active_model_name))[0]
            models[self.active_model_name] = getattr(self.pager, "active_model", None)
            models[clean_name] = getattr(self.pager, "active_model", None)
        return models

    @property
    def _model_id(self) -> str:
        return self.active_model_name or ""

    def load_model(self, model_id: str) -> bool:
        """
        Loads GGUF model via AirLoader hardware profile and AirPager.
        Automatically calculates GPU vs CPU layer allocation.
        """
        # Resolve path
        path = model_id
        models_dir = os.path.expanduser("~/.lmms/models")
        manifests_dir = os.path.expanduser("~/.lmms/manifests")

        # 1. Check manifests first
        manifest_candidate = os.path.join(manifests_dir, f"{model_id}.json")
        if os.path.exists(manifest_candidate):
            try:
                import json
                with open(manifest_candidate, "r") as mf:
                    mdata = json.load(mf)
                    base = mdata.get("base_model")
                    if base:
                        cand = os.path.join(models_dir, base if base.endswith(".gguf") else f"{base}.gguf")
                        if os.path.exists(cand):
                            path = cand
                        elif os.path.exists(os.path.join(models_dir, base)):
                            path = os.path.join(models_dir, base)
            except Exception:
                pass

        # 2. Check direct model file
        if not os.path.exists(path):
            candidate = os.path.join(models_dir, f"{model_id}.gguf")
            if os.path.exists(candidate):
                path = candidate
            elif os.path.exists(os.path.join(models_dir, model_id)):
                path = os.path.join(models_dir, model_id)

        if not os.path.exists(path):
            print(f"[AirLlamaCpp] Error: Model file not found: {path}")
            return False

        profile = self.loader.build_profile(path)
        if not profile:
            print(f"[AirLlamaCpp] Error: Could not generate hardware profile for {path}")
            return False
        success = self.pager.load(profile)
        if success:
            self.active_model_name = profile.model_name
        return success

    def unload_model(self, model_id: Optional[str] = None) -> bool:
        self.pager._park_current()
        self.active_model_name = None
        return True

    def chat(self, model: str, messages: list, stream: bool = False, options: Optional[dict] = None, **kwargs) -> Any:
        context = {
            'messages': messages,
            'target_role': kwargs.get('target_role', 'text'),
            'model': model,
            'model_name': model
        }
        return self.generate(context, stream)

    def generate(self, context: Any, stream: bool = False) -> Any:
        messages = context.get("messages", [])
        model = context.get("model") or context.get("model_name") or self.active_model_name
        if not model and getattr(self, "pager", None) and self.pager.active_profile:
            model = self.pager.active_profile.model_name
        if not model:
            model = "default"
        target_role = context.get("target_role", "text")

        # Ensure model is routed/loaded in scheduler
        self.scheduler.parse_input_and_create_group(1, f"text:{model}")

        result = self.scheduler.route_request(1, target_role, messages)

        def stream_wrapper(gen):
            t0 = time.time()
            tokens = 0
            for item in gen:
                tokens += 1
                yield item
            total_time = time.time() - t0
            tps = tokens / max(total_time, 0.001)

            profile = self.pager.active_profile
            gpu_pct = profile.gpu_pct if profile else 0.0
            cpu_pct = profile.cpu_pct if profile else 100.0
            optimal_gpu_l = profile.optimal_gpu_layers if (profile and profile.optimal_gpu_layers != -1) else (profile.total_layers if profile else 0)
            cpu_l = profile.cpu_layers if profile else 0

            print(f"\n[AirLlamaCpp] Inference finished: {tps:.2f} tokens/sec")
            print(f"[AirLlamaCpp] Allocation: GPU {optimal_gpu_l} layers ({gpu_pct:.1f}%) | CPU DDR5 {cpu_l} layers ({cpu_pct:.1f}%)")

        if stream:
            return stream_wrapper(result)
        else:
            full_content = ""
            for chunk in stream_wrapper(result):
                content = chunk.get("message", {}).get("content", "")
                full_content += content
            return {"message": {"role": "assistant", "content": full_content}}

    def embed(self, text: str) -> List[float]:
        return [0.0]

    def tokenize(self, text: str) -> List[int]:
        if self.pager.active_model and hasattr(self.pager.active_model, "tokenize"):
            try:
                return list(self.pager.active_model.tokenize(text.encode("utf-8")))
            except Exception:
                pass
        return []

    def health(self) -> Dict[str, Any]:
        profile = self.pager.active_profile
        return {
            "engine": "Engine 1: Air + Llama.cpp",
            "active_model": profile.model_name if profile else None,
            "gpu_layers": profile.optimal_gpu_layers if profile else 0,
            "cpu_layers": profile.cpu_layers if profile else 0,
            "regime": profile.regime if profile else 1,
            "gpu_pct": profile.gpu_pct if profile else 0.0,
            "cpu_pct": profile.cpu_pct if profile else 0.0
        }
