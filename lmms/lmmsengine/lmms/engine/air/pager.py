from typing import Optional, Dict, Any
from lmms.engine.air.loader import ModelProfile
from lmms.backend.manager import backend_manager

try:
    from llama_cpp import Llama, LlamaState
except ImportError:
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
            print("[AirPager] mmap enabled: TRUE")
            print("[AirPager] Loading model into execution runtime...")
            self.active_model = Llama(
                model_path=profile.file_path,
                n_gpu_layers=profile.optimal_gpu_layers,
                n_ctx=4096, # Give a solid context window
                use_mmap=True, # Critical for disk-paging
                use_mlock=False, # Allow OS to page to disk
                verbose=False
            )
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
