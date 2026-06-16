import os
import threading
from typing import Dict, Any, Optional
from lmms.engine.runtimes.base import RuntimeContract
try:
    import llama_cpp
    from llama_cpp import Llama, LlamaRAMCache
    import ctypes
    def silent_log_callback(level, text, user_data):
        pass
    # Keep a global reference to prevent garbage collection which causes SegFault!
    _log_callback_wrapper = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(silent_log_callback)
    llama_cpp.llama_log_set(_log_callback_wrapper, ctypes.c_void_p())
except Exception as e:
    print(f"Warning: Failed to import llama_cpp: {e}")
    Llama = None

class LlamaCppRuntime(RuntimeContract):
    def __init__(self):
        self._models: Dict[str, Llama] = {}
        self._global_lock = threading.Lock()

    def load_model(self, model_id: str) -> bool:
        if Llama is None:
            print("ERROR: llama-cpp-python not installed.")
            return False
            
        if model_id in self._models:
            return True
            
        models_dir = os.path.expanduser("~/.lmms/models")
        
        # The engine server now passes the exact path to load_model
        if os.path.exists(model_id):
            full_path = model_id
        else:
            if model_id.endswith(".gguf"):
                file_name = model_id
            else:
                file_name = f"{model_id}.gguf"
            full_path = os.path.join(models_dir, file_name)
        
        if not os.path.exists(full_path):
            print(f"ERROR: Model file not found at {full_path}")
            return False
            
        try:
            model_instance = Llama(
                model_path=full_path,
                n_gpu_layers=-1, # All layers to GPU
                n_ctx=8192,
                flash_attn=True,
                chat_format="chatml",
                verbose=False
            )
            # Use base filename as key if path was given
            key = os.path.basename(full_path).replace(".gguf", "")
            
            # Add cache to avoid re-evaluating system prompt
            cache = LlamaRAMCache(capacity_bytes=1024 * 1024 * 1024) # 1GB Cache
            model_instance.set_cache(cache)
            
            self._models[key] = model_instance
            return True
        except Exception as e:
            print(f"Failed to load model: {e}")
            return False

    def unload_model(self, model_id: str = None) -> bool:
        if model_id:
            if model_id in self._models:
                del self._models[model_id]
        else:
            self._models.clear()
        return True

    def chat(self, model: str, messages: list, stream: bool = False, options: dict = None, **kwargs) -> Any:
        context = {'messages': messages, 'model_name': model}
        return self.generate(context, stream)

    def generate(self, context: Any, stream: bool = False) -> Any:
        model_name = context.get("model_name")
        if not model_name or model_name not in self._models:
            # Fallback to the first loaded model if model_name isn't strictly matched
            if self._models:
                model_name = list(self._models.keys())[0]
            else:
                raise RuntimeError("No model is currently loaded in LlamaCppRuntime.")
                
        active_model = self._models[model_name]
            
        # Extract messages from context
        # Standardize expected context: {"messages": [...]}
        messages = list(context.get("messages", []))
        mode = context.get("mode", "deep")
        think = context.get("think", True)
        
        # Inject system prompt if not present
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            sys_msg = "You are a helpful AI assistant."
            if mode == "code":
                sys_msg = "You are an expert programmer. Write clean, efficient, and well-documented code. Do not use conversational filler."
            elif mode == "research":
                sys_msg = "You are an expert researcher. Provide highly detailed, accurate, and analytical answers with logical structuring."
            elif mode == "fast":
                sys_msg = "You are a fast and concise assistant. Answer directly without thinking or explanation."
            
            if think is False and mode not in ["fast"]:
                sys_msg += " Do not output any thought process or <think> tags. Answer directly."
                
            messages.insert(0, {"role": "system", "content": sys_msg})

        
        if stream:
            def stream_response():
                with self._global_lock:
                    response_generator = active_model.create_chat_completion(
                        messages=messages,
                        stream=True,
                        max_tokens=1024
                    )
                while True:
                    with self._global_lock:
                        try:
                            chunk = next(response_generator)
                        except StopIteration:
                            break
                        except Exception as e:
                            print(f"Error during stream generation: {e}")
                            break
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content")
                        if token:
                            yield {"message": {"role": "assistant", "content": token}}
            return stream_response()
        else:
            with self._global_lock:
                response = active_model.create_chat_completion(
                    messages=messages,
                    stream=False,
                    max_tokens=1024
                )
            return {"message": {"content": response["choices"][0]["message"]["content"]}}

    def embed(self, text: str) -> list[float]:
        # Dummy for now
        return [0.0]

    def tokenize(self, text: str) -> list[int]:
        if self._models:
            first_model = list(self._models.values())[0]
            return first_model.tokenize(text.encode("utf-8"))
        return []

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok" if Llama else "missing_dependency",
            "backend": "llama.cpp",
            "models_loaded": len(self._models),
            "model_paths": list(self._models.keys())
        }
