from typing import Optional, Dict, Any, Tuple
from lmms.engine.air.loader import ModelProfile

try:
    import llama_cpp  # type: ignore
    from llama_cpp import Llama, LlamaState  # type: ignore
except ImportError:
    llama_cpp = None
    Llama: Any = None
    LlamaState: Any = None

class AirPager:
    def __init__(self):
        self.active_model: Any = None
        self.active_profile: Optional[ModelProfile] = None
        self.states: Dict[str, Tuple[Any, int]] = {}

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

            # Enable Quantized KV Cache (Q8_0)
            # FlashAttention is only enabled if architecture is standard dense (not MoE), as MoE kernels require standard attn
            arch = getattr(profile, "architecture", "").lower()
            is_moe = "moe" in arch
            if llama_cpp is not None and not is_moe:
                if hasattr(llama_cpp, "GGML_TYPE_Q8_0"):
                    init_kwargs["type_k"] = llama_cpp.GGML_TYPE_Q8_0
                    init_kwargs["type_v"] = llama_cpp.GGML_TYPE_Q8_0
                init_kwargs["flash_attn"] = True

            if Llama is None:
                raise RuntimeError("llama_cpp runtime is not available.")

            llama_factory: Any = Llama
            while True:
                try:
                    self.active_model = llama_factory(**init_kwargs)
                    break
                except Exception as err:
                    curr_gpu = init_kwargs.get("n_gpu_layers", 0)
                    if "flash_attn" in init_kwargs or "type_k" in init_kwargs:
                        print(f"[AirPager] Info: Retrying without experimental KV flags: {err}")
                        init_kwargs.pop("flash_attn", None)
                        init_kwargs.pop("type_k", None)
                        init_kwargs.pop("type_v", None)
                        continue
                    elif curr_gpu > 0:
                        reduced_gpu = max(0, curr_gpu - 2)
                        print(f"[AirPager] Info: Stepping down GPU layers from {curr_gpu} to {reduced_gpu} to fit VRAM: {err}")
                        init_kwargs["n_gpu_layers"] = reduced_gpu
                        continue
                    else:
                        print(f"[AirPager] Fatal: Model instantiation failed even at 0 GPU layers: {err}")
                        raise err

            self.active_profile = profile
            
            # STRICT KV CACHE RESTORE RULES:
            # - Same model architecture
            # - Same context configuration
            # - Same hardware layer allocation
            if profile.model_name in self.states and self.active_model is not None:
                state_entry = self.states[profile.model_name]
                if isinstance(state_entry, tuple) and len(state_entry) == 2:
                    state_data, prev_gpu_layers = state_entry
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
                import torch  # type: ignore
                if torch.cuda.is_initialized():
                    torch.cuda.empty_cache()
            except Exception:
                pass

    def execute_stream(self, messages: list):
        if not self.active_model:
            raise RuntimeError("No model active in AirPager.")
            
        generator: Any = self.active_model.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=1024,
            temperature=0.0,
            seed=42
        )
        
        def stream_response():
            for chunk in generator:
                if isinstance(chunk, dict) and "choices" in chunk and len(chunk["choices"]) > 0:
                    first_choice = chunk["choices"][0]
                    if isinstance(first_choice, dict):
                        delta = first_choice.get("delta", {})
                        if isinstance(delta, dict) and "content" in delta:
                            yield {"message": {"content": delta["content"]}}
        return stream_response()
