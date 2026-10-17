import os
import threading
import io
import base64
from typing import Dict, Any, Optional

try:
    from PIL import Image
    import torch
except ImportError:
    Image: Any = None
    torch: Any = None

from lmms.engine.core.base import RuntimeContract

class HfVisionRuntime(RuntimeContract):
    def __init__(self):
        self._loaded_models: Dict[str, Any] = {}
        self._global_lock = threading.Lock()

    @property
    def _models(self) -> Dict[str, Any]:
        return self._loaded_models
        
    def load_model(self, model_id: str) -> bool:
        # Import inside to avoid slow startup for non-vision users
        try:
            os.environ["TRANSFORMERS_VERBOSITY"] = "error"
            os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=FutureWarning)
            
            from transformers import AutoProcessor, BitsAndBytesConfig
            try:
                from transformers import AutoModelForImageTextToText  # type: ignore
            except ImportError:
                from transformers import AutoModelForVision2Seq as AutoModelForImageTextToText  # type: ignore
            import logging
            logging.getLogger("transformers").setLevel(logging.ERROR)
        except ImportError:
            print("ERROR: transformers or bitsandbytes not installed.")
            return False
            
        if model_id in self._loaded_models:
            return True
            
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16 if torch else None
            )
            
            processor = AutoProcessor.from_pretrained(model_id)
            model = AutoModelForImageTextToText.from_pretrained(
                model_id,
                device_map="auto",
                quantization_config=quantization_config
            )
            
            self._loaded_models[model_id] = {
                "processor": processor,
                "model": model
            }
            self._loaded_models["active"] = self._loaded_models[model_id]
            return True
        except Exception as e:
            print(f"ERROR: Failed to load PyTorch Vision Model: {e}")
            return False

    def unload_model(self, model_id: Optional[str] = None) -> bool:
        if model_id and model_id in self._loaded_models:
            del self._loaded_models[model_id]
        else:
            self._loaded_models.clear()
        if "active" in self._loaded_models:
            del self._loaded_models["active"]
        # Optionally free CUDA memory
        try:
            if torch and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        return True

    def chat(self, model: str, messages: list, stream: bool = False, options: Optional[dict] = None, **kwargs) -> Any:
        context = {'messages': messages, 'model_name': model}
        return self.generate(context, stream)

    def generate(self, context: Any, stream: bool = False) -> Any:
        if "active" not in self._models:
            if stream:
                def err():
                    yield {"message": {"content": "Error: No vision model loaded."}}
                return err()
            return {"message": {"content": "Error: No vision model loaded."}}
            
        processor = self._models["active"]["processor"]
        model = self._models["active"]["model"]
        
        messages = context.get("messages", [])
        images = []
        processed_messages = []
        
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                new_content = []
                for item in content:
                    if item.get("type") == "image_url":
                        url = item["image_url"]["url"]
                        if url.startswith("data:image"):
                            b64_data = url.split(",")[1]
                            image_data = base64.b64decode(b64_data)
                            image = Image.open(io.BytesIO(image_data)).convert("RGB")
                            images.append(image)
                            new_content.append({"type": "image"})
                    elif item.get("type") == "text":
                        new_content.append({"type": "text", "text": item["text"]})
                processed_messages.append({"role": msg["role"], "content": new_content})
            else:
                processed_messages.append(msg)
                
        # Generate prompt using processor
        prompt = processor.apply_chat_template(processed_messages, add_generation_prompt=True)
        
        # Prepare inputs
        if len(images) > 0:
            inputs = processor(text=prompt, images=images, return_tensors="pt")
        else:
            inputs = processor(text=prompt, return_tensors="pt")
            
        # Cast floating point tensors to match model dtype (e.g. float16)
        for k, v in inputs.items():
            if torch.is_tensor(v) and v.is_floating_point():
                inputs[k] = v.to(model.dtype)
                
        inputs = inputs.to(model.device)
        
        if stream:
            from transformers import TextIteratorStreamer
            streamer = TextIteratorStreamer(processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
            generation_kwargs = dict(inputs, streamer=streamer, max_new_tokens=500)
            
            def generate_and_catch_errors(**kwargs):
                try:
                    model.generate(**kwargs)
                except Exception as e:
                    print(f"\n[hf_vision error] model.generate failed: {e}")
                finally:
                    streamer.end()
            
            thread = threading.Thread(target=generate_and_catch_errors, kwargs=generation_kwargs)
            thread.start()
            
            def stream_response():
                for new_text in streamer:
                    if new_text:
                        yield {"message": {"role": "assistant", "content": new_text}}
            return stream_response()
        else:
            generated_ids = model.generate(**inputs, max_new_tokens=500)
            generated_texts = processor.batch_decode(generated_ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            return {"message": {"content": generated_texts[0]}}
            
    def embed(self, text: str) -> list[float]:
        return [0.0]

    def tokenize(self, text: str) -> list[int]:
        return []

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok" if self._models else "not_loaded",
            "backend": "transformers (pytorch)",
            "models_loaded": len([k for k in self._models.keys() if k != "active"]),
            "model_paths": [k for k in self._models.keys() if k != "active"]
        }
