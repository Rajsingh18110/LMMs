import os
import json
import time
import requests

CACHE_FILE = os.path.expanduser("~/.lmms/hf_cache.json")
CACHE_TTL = 86400  # 24 hours in seconds

class ModelCache:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    @staticmethod
    def _load_cache() -> dict:
        if not os.path.exists(CACHE_FILE):
            return {}
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def _save_cache(cache: dict):
        ModelCache._ensure_dir()
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f)
        except Exception:
            pass

    @staticmethod
    def fetch_model_info(model_id: str, force_refresh=False) -> dict:
        cache = ModelCache._load_cache()
        now = time.time()
        
        # Return cached if valid
        if not force_refresh and model_id in cache:
            entry = cache[model_id]
            if now - entry.get("timestamp", 0) < CACHE_TTL:
                return entry.get("data", {})

        # Fetch from HF API
        try:
            url = f"https://huggingface.co/api/models/{model_id}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            # Fetch README
            readme_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
            readme_resp = requests.get(readme_url, timeout=10)
            if readme_resp.status_code == 200:
                data["readme"] = readme_resp.text
            else:
                data["readme"] = "*No README available.*"
                
            cache[model_id] = {
                "timestamp": now,
                "data": data
            }
            ModelCache._save_cache(cache)
            return data
        except Exception as e:
            print(f"Failed to fetch model info for {model_id}: {e}")
            # Return stale cache if available
            if model_id in cache:
                return cache[model_id].get("data", {})
            return {"error": str(e), "readme": "*Failed to fetch data.*"}

    @staticmethod
    def fetch_trending_models(category: str, force_refresh=False, query: str = "") -> list:
        cache_key = f"trending_{category}_{query}"
        cache = ModelCache._load_cache()
        now = time.time()
        
        if not force_refresh and cache_key in cache:
            entry = cache[cache_key]
            if now - entry.get("timestamp", 0) < CACHE_TTL:
                return entry.get("data", [])

        try:
            base_url = "https://huggingface.co/api/models"
            params = {
                "sort": "downloads",
                "direction": "-1",
                "limit": 30
            }
            
            if category == "Text":
                params["search"] = "GGUF"
                params["pipeline_tag"] = "text-generation"
            elif category == "Image":
                params["pipeline_tag"] = "text-to-image"
            elif category == "Video":
                params["pipeline_tag"] = "text-to-video"
            elif category == "Audio":
                params["pipeline_tag"] = "text-to-audio"
            elif category == "Multimodal":
                params["pipeline_tag"] = "image-to-text"
            elif category == "Reasoning":
                params["search"] = "GGUF"
                params["tags"] = "reasoning"
            elif category == "Coding":
                params["search"] = "GGUF"
                params["tags"] = "code"
                
            if query:
                params["search"] = query
                
            resp = requests.get(base_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            models = []
            for item in data:
                models.append({
                    "id": item.get("_id"),
                    "modelId": item.get("id"),
                    "downloads": item.get("downloads", 0),
                    "likes": item.get("likes", 0),
                    "lastModified": item.get("lastModified", ""),
                    "tags": item.get("tags", [])
                })
                
            cache[cache_key] = {
                "timestamp": now,
                "data": models
            }
            ModelCache._save_cache(cache)
            return models
        except Exception as e:
            print(f"Failed to fetch trending models: {e}")
            if cache_key in cache:
                return cache[cache_key].get("data", [])
            return []

    @staticmethod
    def fetch_model_files(model_id: str) -> list:
        try:
            url = f"https://huggingface.co/api/models/{model_id}/tree/main"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            files = []
            for item in data:
                if item.get("type") == "file":
                    path = item.get("path", "")
                    if path.endswith(".gguf") or path.endswith(".safetensors"):
                        files.append({
                            "filename": path,
                            "size": item.get("size", 0)
                        })
            return files
        except Exception as e:
            print(f"Failed to fetch files for {model_id}: {e}")
            return []
