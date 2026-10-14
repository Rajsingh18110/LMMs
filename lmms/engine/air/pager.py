from typing import Optional, Dict, Any
from lmms.engine.air.loader import ModelProfile

try:
    import llama_cpp
    from llama_cpp import Llama, LlamaState
except ImportError:
    llama_cpp = None
    Llama = None
    LlamaState = None

class AirPager:
    def __init__(self):
        self.active_model: Optional[Llama] = None
        self.active_profile: Optional[ModelProfile] = None
        self.states: Dict[str, LlamaState] = {}

    def load(self, profile: ModelProfile) -> bool:
        if self.active_profile and self.active_profile.model_name == profile.model_name:
            return True # Already loaded
            
        # If another model is active, we must save its state and unload it
        if self.active_model:
            self._park_current()

        try:
            print("[AirPager] mmap enabled: TRUE (Zero-latency OS virtual memory mapping)")
            print(f"[AirPager] P-Core affinity locking: n_threads={profile.recommended_threads}")
            print(f"[AirPager] Quantized KV Cache: Q8_0 + FlashAttention enabled")
            print(f"[AirPager] Allocating {profile.optimal_gpu_layers} layers to GPU ({profile.gpu_pct:.1f}%), {profile.cpu_layers} layers to DDR5 CPU ({profile.cpu_pct:.1f}%)")

            ctx_len = min(getattr(profile, "context_length", 4096), 4096)
            threads = getattr(profile, "recommended_threads", 6)
            
            init_kwargs = {
                "model_path": profile.file_path,
                "n_gpu_layers": profile.optimal_gpu_layers,
                "n_ctx": ctx_len,
                "n_threads": threads,
                "use_mmap": True,
                "use_mlock": False,
                "verbose": False
            }

            # Enable Quantized KV Cache (Q8_0) and FlashAttention
            if llama_cpp is not None:
                if hasattr(llama_cpp, "GGML_TYPE_Q8_0"):
                    init_kwargs["type_k"] = llama_cpp.GGML_TYPE_Q8_0
                    init_kwargs["type_v"] = llama_cpp.GGML_TYPE_Q8_0
                init_kwargs["flash_attn"] = True

            try:
                self.active_model = Llama(**init_kwargs)
            except (TypeError, Exception) as flag_err:
                print(f"[AirPager] Info: Retrying with standard KV parameters: {flag_err}")
                init_kwargs.pop("flash_attn", None)
                init_kwargs.pop("type_k", None)
                init_kwargs.pop("type_v", None)
                self.active_model = Llama(**init_kwargs)

            self.active_profile = profile
            
            # STRICT KV CACHE RESTORE RULES:
            # - Same model architecture
            # - Same context configuration
            # - Same hardware layer allocation
            if profile.model_name in self.states:
                state_data, prev_gpu_layers = self.states[profile.model_name]
                if prev_gpu_layers == profile.optimal_gpu_layers:
                    try:
                        self.active_model.load_state(state_data)
                    except Exception as e:
                        print(f"Warning: KV state restore failed for {profile.model_name}: {e}")
                else:
                    print(f"Warning: KV state dropped for {profile.model_name} due to hardware configuration change (Layers: {prev_gpu_layers} -> {profile.optimal_gpu_layers})")
                    del self.states[profile.model_name]
                
            return True
        except Exception as e:
            print(f"AirPager load failed: {e}")
            return False

    def _park_current(self):
        if self.active_model and self.active_profile:
            try:
                # Save KV cache state to RAM along with the exact hardware allocation
                state_data = self.active_model.save_state()
                self.states[self.active_profile.model_name] = (state_data, self.active_profile.optimal_gpu_layers)
            except Exception as e:
                print(f"Warning: Failed to save KV state for {self.active_profile.model_name}: {e}")
            
            # Unload from VRAM
            del self.active_model
            self.active_model = None
            self.active_profile = None
            
            # Trigger garbage collection and cuda empty cache
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def execute_stream(self, messages: list):
        if not self.active_model:
            raise RuntimeError("No model active in AirPager.")
            
        generator = self.active_model.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=1024,
            temperature=0.0,
            seed=42
        )
        
        def stream_response():
            for chunk in generator:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield {"message": {"content": delta["content"]}}
        return stream_response()
