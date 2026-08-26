import re

with open("lmms/engine/runtimes/llama_cpp.py", "r") as f:
    code = f.read()

# Fix model name lookup
old_model_name = """    def generate(self, context: Any, stream: bool = False) -> Any:
        model_name = context.get("model_name")
        if not model_name or model_name not in self._models:
            # Fallback to the first loaded model if model_name isn't strictly matched
            if self._models:
                model_name = list(self._models.keys())[0]
            else:
                raise RuntimeError("No model is currently loaded in LlamaCppRuntime.")

        active_model = self._models[model_name]"""

new_model_name = """    def generate(self, context: Any, stream: bool = False) -> Any:
        model_name = context.get("model_name")
        
        loaded_model_key = None
        if model_name:
            search_name = model_name.replace(":", "-").lower()
            with self._global_lock:
                for k in self._models.keys():
                    if search_name in k.lower() or k.lower() in search_name:
                        loaded_model_key = k
                        break

        if not loaded_model_key:
            # Fallback to the first loaded model if model_name isn't strictly matched
            if self._models:
                loaded_model_key = list(self._models.keys())[0]
            else:
                raise RuntimeError("No model is currently loaded in LlamaCppRuntime.")

        active_model = self._models[loaded_model_key]"""

code = code.replace(old_model_name, new_model_name)

# Fix stream generation
old_stream = """            def stream_response():
                with self._global_lock:
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
                                print(f"\\n--- REPETITION SAFETY-NET TRIGGERED ---")
                                print(f"Recent Tokens Array: {recent_tokens}")
                                print(f"Matched Window Size: {w}")
                                print(f"Accumulated Text snippet: {accumulated_text[-200:]}")
                                print("---------------------------------------\\n")
                                print("Model repetition detected, generation stopped early.")
                                yield {"message": {"role": "assistant", "content": "\\n\\n[System: Model repeated itself, please rephrase your question or switch model.]"}}
                                break

                            yield {"message": {"role": "assistant", "content": token}}
            return stream_response()"""

new_stream = """            def stream_response():
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
                                    print(f"\\n--- REPETITION SAFETY-NET TRIGGERED ---")
                                    print(f"Recent Tokens Array: {recent_tokens}")
                                    print(f"Matched Window Size: {w}")
                                    print(f"Accumulated Text snippet: {accumulated_text[-200:]}")
                                    print("---------------------------------------\\n")
                                    print("Model repetition detected, generation stopped early.")
                                    yield {"message": {"role": "assistant", "content": "\\n\\n[System: Model repeated itself, please rephrase your question or switch model.]"}}
                                    break

                                yield {"message": {"role": "assistant", "content": token}}
                finally:
                    self._global_lock.release()
            return stream_response()"""

code = code.replace(old_stream, new_stream)

with open("lmms/engine/runtimes/llama_cpp.py", "w") as f:
    f.write(code)
