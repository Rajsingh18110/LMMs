from typing import List, Dict, Any
from lmms.backend.memory.providers.sqlite import Memory
import requests

ENGINE_URL = "http://localhost:11435"

class PairManager:
    def __init__(self, memory_provider: Memory):
        self.memory = memory_provider
        self.active_pairs = {}
        
    def define_pair(self, pair_slot: int, models: Dict[str, str]):
        """
        Define a pair of models for a slot.
        e.g., models = {"text": "qwen3:8b", "vision": "llava:13b"}
        """
        self.active_pairs[pair_slot] = models
        
    def execute_pair(self, pair_slot: int, chat_id: str, prompt: str, image_path: str = None) -> dict:
        """
        Executes models in the pair simultaneously or sequentially, 
        and saves all their outputs to the exact same chat_id memory context.
        """
        if pair_slot not in self.active_pairs:
            raise ValueError(f"Pair slot {pair_slot} not defined.")
            
        models = self.active_pairs[pair_slot]
        results = {}
        
        # In a real async environment, these would be fired simultaneously via asyncio.
        # For simplicity, we fire them sequentially.
        
        if "text" in models:
            text_model = models["text"]
            # Fetch past context for this specific chat
            history = self.memory.get_history(chat_id, limit=10)
            messages = history + [{"role": "user", "content": prompt}]
            
            try:
                resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                    "model_name": text_model,
                    "messages": messages,
                    "stream": False
                })
                resp.raise_for_status()
                text_response = resp.json()
                # Save the model's response to the shared memory context
                content = text_response.get("message", {}).get("content", "")
                self.memory.save(chat_id, "assistant", content, model=text_model)
                results["text"] = content
            except Exception as e:
                results["text"] = f"Failed to execute {text_model}: {str(e)}"
                
        if "vision" in models and image_path:
            vision_model = models["vision"]
            # Vision models often just take the image and a specific prompt
            history = self.memory.get_history(chat_id, limit=10)
            messages = history + [{"role": "user", "content": f"Analyze this image: {image_path}. Prompt: {prompt}"}]
            
            try:
                resp = requests.post(f"{ENGINE_URL}/v1/chat/completions", json={
                    "model_name": vision_model,
                    "messages": messages,
                    "stream": False
                })
                resp.raise_for_status()
                vision_response = resp.json()
                content = vision_response.get("message", {}).get("content", "")
                self.memory.save(chat_id, "assistant", f"[Vision Analysis]: {content}", model=vision_model)
                results["vision"] = content
            except Exception as e:
                results["vision"] = f"Failed to execute {vision_model}: {str(e)}"
                
        return results
