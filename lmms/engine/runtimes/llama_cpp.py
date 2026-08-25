import os
import re
import threading
from typing import Dict, Any, Optional
from lmms.engine.runtimes.base import RuntimeContract
from lmms.engine.response_cleaner import strip_hidden_reasoning
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

    def _detect_chat_format(self, model_path: str) -> Optional[str]:
        filename = os.path.basename(model_path).lower()
        if any(token in filename for token in ["qwen3", "qwen2", "qwen"]):
            return "chatml"
        if "llama" in filename:
            return "llama-2"
        if "chatml" in filename:
            return "chatml"
        return None

    def _strip_hidden_reasoning(self, text: str) -> str:
        return strip_hidden_reasoning(text)

    def load_model(self, model_id: str) -> bool:
        with self._global_lock:
            return self._load_model_internal(model_id)

    def _load_model_internal(self, model_id: str) -> bool:
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
            
        file_size_gb = os.path.getsize(full_path) / (1024**3)
        vram_gb = 0
        try:
            import torch
            if torch.cuda.is_available():
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        except Exception:
            pass

        # Check System RAM
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        
        # Calculate safe n_ctx and display warning if necessary
        safe_n_ctx = 8192 # Default safe limit instead of 0 (native max)
        
        mem_gb = max(vram_gb, ram_gb)
        
        if mem_gb > 0:
            print(f"\n[TIMING LOG] Detected file_size_gb: {file_size_gb:.2f}GB, System RAM: {ram_gb:.2f}GB, VRAM: {vram_gb:.2f}GB, mem_gb limit used: {mem_gb:.2f}GB")
            if file_size_gb > mem_gb * 1.5:
                import time
                print(f"\n\033[91mWARNING: You are attempting to run a massive model ({file_size_gb:.1f}GB) on a machine with limited memory ({mem_gb:.1f}GB).\033[0m")
                print("\033[91mThis will cause heavy system RAM swapping, leading to extremely slow generation.\033[0m")
                print("\033[91mSustained 100% GPU/CPU thrashing may overheat or damage your hardware over time.\033[0m")
                print("\033[93mProceeding in 5 seconds...\033[0m\n")
                time.sleep(5)
            
            # Cap n_ctx dynamically based on available memory to prevent KV cache OOM
            if mem_gb < 8.0:
                safe_n_ctx = 4096
            elif mem_gb < 16.0:
                safe_n_ctx = 8192
            elif mem_gb < 32.0:
                safe_n_ctx = 16384
            else:
                safe_n_ctx = 32768
                
        current_ctx = safe_n_ctx
        model_instance = None
        first_try = True
        attempt = 1
        import time
        while current_ctx >= 512 or first_try:
            try:
                kwargs = {
                    "model_path": full_path,
                    "n_gpu_layers": -1,
                    "n_ctx": current_ctx,
                    "flash_attn": True,
                    "verbose": False
                }
                # Initial guess for chat_format based on filename.
                # This llama-cpp-python build exposes the Qwen handler as "qwen".
                detected_format = self._detect_chat_format(full_path)
                if detected_format:
                    kwargs["chat_format"] = detected_format
                elif "chatml" in os.path.basename(full_path).lower():
                    kwargs["chat_format"] = "chatml"
                elif "llama" in os.path.basename(full_path).lower():
                    kwargs["chat_format"] = "llama-2"
                    kwargs["chat_format"] = "chatml"
                
                print(f"[TIMING LOG] Attempt {attempt}: Loading Llama with n_ctx={current_ctx}, n_gpu_layers=-1...")
                start_time = time.time()
                model_instance = Llama(**kwargs)
                end_time = time.time()
                print(f"[TIMING LOG] Attempt {attempt} SUCCEEDED in {end_time - start_time:.2f}s")
                break
            except Exception as e:
                end_time = time.time()
                print(f"[TIMING LOG] Attempt {attempt} FAILED in {end_time - start_time:.2f}s: {e}")
                attempt += 1
                err_msg = str(e).lower()
                if "llama_context" in err_msg or "kv cache" in err_msg or "memory" in err_msg or "alloc" in err_msg:
                    if current_ctx == 0:
                        current_ctx = 8192
                        print(f"\033[93m[Fallback]\033[0m Native context too large for RAM/VRAM, retrying with {current_ctx}...")
                    else:
                        print(f"\033[93m[Fallback]\033[0m Context {current_ctx} too large for RAM/VRAM, retrying with {current_ctx // 2}...")
                        current_ctx //= 2
                    first_try = False
                else:
                    print(f"Failed to load model: {e}")
                    return False
                    
        if not model_instance:
            print("Failed to load model: Insufficient memory to create context even at lowest settings.")
            return False
            
        # Use base filename as key if path was given
        key = os.path.basename(full_path).replace(".gguf", "")
        
        # Check for chat template in metadata to prepare fallback stop tokens
        metadata = getattr(model_instance, "metadata", {})
        has_chat_template = False
        for k in metadata.keys():
            if "tokenizer.chat_template" in k:
                has_chat_template = True
                break
                
        if not hasattr(self, "_model_fallback_stops"):
            self._model_fallback_stops = {}
            
        if not has_chat_template:
            self._model_fallback_stops[key] = ["<|im_end|>", "</s>", "<|endoftext|>"]
            # Apply Burst/format fallback when metadata lacks a template. Qwen GGUFs
            # need the registered qwen chat format in this llama-cpp-python build.
            if "chat_format" not in kwargs:
                fallback_format = self._detect_chat_format(full_path) or "chatml"
                print(f"[Fallback] No chat_template found in metadata for {key}. Reloading with fallback '{fallback_format}' format to prevent infinite repetition.")
                del model_instance
                kwargs["chat_format"] = fallback_format
                model_instance = Llama(**kwargs)
        else:
            self._model_fallback_stops[key] = None

        # Add cache to avoid re-evaluating system prompt
        # cache = LlamaRAMCache(capacity_bytes=1024 * 1024 * 1024) # 1GB Cache
        # model_instance.set_cache(cache)
        
        self._models[key] = model_instance
        return True
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

        # Estimate token count to prevent C++ crash
        total_tokens = 0
        try:
            for m in messages:
                content = m.get("content", "")
                if isinstance(content, list):
                    for part in content:
                        if part.get("type") == "text":
                            total_tokens += len(active_model.tokenize(part.get("text", "").encode("utf-8")))
                else:
                    total_tokens += len(active_model.tokenize(str(content).encode("utf-8")))
            
            total_tokens += len(messages) * 10 # Chat template overhead
            
            if total_tokens > active_model.n_ctx() - 128:
                err_msg = f"Context length exceeded! Prompt is ~{total_tokens} tokens, but model context (n_ctx) is {active_model.n_ctx()}."
                if stream:
                    def err_stream():
                        yield {"message": {"role": "assistant", "content": f"\n\n❌ **Engine Error**: {err_msg}"}}
                    return err_stream()
                else:
                    return {"message": {"content": f"\n\n❌ **Engine Error**: {err_msg}"}}
        except Exception as e:
            pass # Tokenization failed, just proceed and let the engine handle it
        
        # Prepare context-aware repeat penalty
        repeat_penalty = context.get("repetition_penalty") or (1.05 if mode == "code" else 1.1)
        temperature = context.get("temperature")
        top_p = context.get("top_p")
        
        # Prepare fallback stop tokens
        fallback_stops = getattr(self, "_model_fallback_stops", {}).get(model_name)
        stop_tokens = fallback_stops if fallback_stops else []
        
        # Determine model file size for dynamic thresholds
        try:
            model_path = active_model.model_path
            size_gb = os.path.getsize(model_path) / (1024**3)
            if size_gb < 2.0:
                default_repeats = 6
                default_window = 4
            elif size_gb < 8.0:
                default_repeats = 5
                default_window = 5
            else:
                default_repeats = 4
                default_window = 5
        except Exception:
            default_repeats = 4
            default_window = 5
            
        ngram_window = context.get("ngram_window", default_window)
        max_repeats = context.get("ngram_repeats", default_repeats)

        if stream:
            def stream_response():
                self._global_lock.acquire()
                try:
                    response_generator = active_model.create_chat_completion(
                        messages=messages,
                        stream=True,
                        max_tokens=context.get("max_tokens", max(1024, int(active_model.n_ctx() * 0.18) if active_model.n_ctx() > 0 else 1024)),
                        repeat_penalty=repeat_penalty,
                        temperature=temperature if temperature is not None else 0.7,
                        top_p=top_p if top_p is not None else 0.95,
                        stop=stop_tokens
                    )
                
                    recent_tokens = []
                    accumulated_text = ""
                    yielded_text = ""
                    
                    while True:
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
                                if not think and mode not in ["fast"]:
                                    accumulated_text += token
                                    cleaned = self._strip_hidden_reasoning(accumulated_text)
                                    if len(cleaned) > len(yielded_text):
                                        token = cleaned[len(yielded_text):]
                                        yielded_text = cleaned
                                    else:
                                        continue

                                # N-gram repetition tracker
                                recent_tokens.append(token)
                                if len(recent_tokens) > ngram_window * max_repeats:
                                    recent_tokens.pop(0)
                                
                                # Check for repetition dynamically for sizes from 1 up to ngram_window
                                is_repeating = False
                                for w in range(1, ngram_window + 1):
                                    if len(recent_tokens) >= w * max_repeats:
                                        is_rep = True
                                        window = recent_tokens[-w:]
                                        for i in range(1, max_repeats):
                                            start = -(i + 1) * w
                                            end = -i * w
                                            prev_window = recent_tokens[start:end] if end != 0 else recent_tokens[start:]
                                            if window != prev_window:
                                                is_rep = False
                                                break
                                        if is_rep:
                                            window_str = "".join(window)
                                            import string
                                            is_only_punct = all(c in string.punctuation or c.isspace() for c in window_str)
                                            
                                            if len(window_str) < 15 or is_only_punct:
                                                # False positive due to short/punctuation sequence
                                                is_rep = False
                                            else:
                                                is_repeating = True
                                                break

                                if is_repeating:
                                    print(f"\n--- REPETITION SAFETY-NET TRIGGERED ---")
                                    print(f"Recent Tokens Array: {recent_tokens}")
                                    print(f"Matched Window Size: {w}")
                                    print(f"Accumulated Text snippet: {accumulated_text[-200:]}")
                                    print("---------------------------------------\n")
                                    print("Model repetition detected, generation stopped early.")
                                    yield {"message": {"role": "assistant", "content": "\n\n[System: Model repeated itself, please rephrase your question or switch model.]"}}
                                    break

                                yield {"message": {"role": "assistant", "content": token}}
                finally:
                    self._global_lock.release()
            return stream_response()
        else:
            with self._global_lock:
                response = active_model.create_chat_completion(
                    messages=messages,
                    stream=False,
                    max_tokens=context.get("max_tokens", max(1024, int(active_model.n_ctx() * 0.18) if active_model.n_ctx() > 0 else 1024)),
                    repeat_penalty=repeat_penalty,
                    temperature=temperature if temperature is not None else 0.7,
                    top_p=top_p if top_p is not None else 0.95,
                    stop=stop_tokens
                )
            content = response["choices"][0]["message"]["content"]
            if not think and mode not in ["fast"]:
                content = self._strip_hidden_reasoning(content)
            return {"message": {"content": content}}

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
