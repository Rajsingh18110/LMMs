import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# We will migrate to this file or use it as the new standard
REGISTRY_FILE = os.path.expanduser("~/.lmms/models.json")

class ModelRegistry:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)

    @staticmethod
    def _load_raw() -> Dict[str, Any]:
        if not os.path.exists(REGISTRY_FILE):
            return {}
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def _save_raw(data: Dict[str, Any]):
        ModelRegistry._ensure_dir()
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def register(model_id: str, provider_id: str, display_name: str, modality: str, capabilities: Dict[str, bool], **kwargs) -> str:
        """Registers or updates a model in the registry."""
        data = ModelRegistry._load_raw()
        
        # Use provider_id + model_id as a unique internal ID
        internal_id = f"{provider_id}::{model_id}"
        
        model_entry = data.get(internal_id, {})
        model_entry.update({
            "id": internal_id,
            "provider_id": provider_id,
            "model_id": model_id,
            "display_name": display_name,
            "modality": modality,
            "capabilities": {
                "text": capabilities.get("text", True),
                "vision": capabilities.get("vision", False),
                "image_generation": capabilities.get("image_generation", False),
                "video_generation": capabilities.get("video_generation", False),
                "voice": capabilities.get("voice", False),
                "streaming": capabilities.get("streaming", True),
                "tools": capabilities.get("tools", False),
                "thinking": capabilities.get("thinking", False)
            },
            "context_window": kwargs.get("context_window", 4096),
            "max_output_tokens": kwargs.get("max_output_tokens", 4096),
            "thinking_supported": capabilities.get("thinking", False),
            "thinking_default": kwargs.get("thinking_default", False),
            "streaming_supported": capabilities.get("streaming", True),
            "pricing": kwargs.get("pricing", {}),
            "enabled": kwargs.get("enabled", True),
            "metadata": kwargs.get("metadata", {}),
            "updated_at": datetime.utcnow().isoformat()
        })
        
        if "created_at" not in model_entry:
            model_entry["created_at"] = datetime.utcnow().isoformat()
            
        data[internal_id] = model_entry
        ModelRegistry._save_raw(data)
        return internal_id

    @staticmethod
    def update(internal_id: str, updates: Dict[str, Any]) -> bool:
        data = ModelRegistry._load_raw()
        if internal_id not in data:
            return False
            
        model = data[internal_id]
        for k, v in updates.items():
            if k in ["display_name", "modality", "capabilities", "context_window", "max_output_tokens", "thinking_default", "enabled", "pricing", "metadata"]:
                model[k] = v
        
        model["updated_at"] = datetime.utcnow().isoformat()
        ModelRegistry._save_raw(data)
        return True

    @staticmethod
    def get(internal_id: str) -> Optional[Dict[str, Any]]:
        return ModelRegistry._load_raw().get(internal_id)

    @staticmethod
    def list() -> List[Dict[str, Any]]:
        return list(ModelRegistry._load_raw().values())

    @staticmethod
    def delete(internal_id: str) -> bool:
        data = ModelRegistry._load_raw()
        if internal_id in data:
            del data[internal_id]
            ModelRegistry._save_raw(data)
            return True
        return False

    @staticmethod
    def enable(internal_id: str) -> bool:
        return ModelRegistry.update(internal_id, {"enabled": True})

    @staticmethod
    def disable(internal_id: str) -> bool:
        return ModelRegistry.update(internal_id, {"enabled": False})

    @staticmethod
    def find_by_capability(capability: str) -> List[Dict[str, Any]]:
        results = []
        for m in ModelRegistry.list():
            if not m.get("enabled", True):
                continue
            caps = m.get("capabilities", {})
            if isinstance(caps, dict) and caps.get(capability):
                results.append(m)
            elif isinstance(caps, list) and capability.lower() in [c.lower() for c in caps]:
                results.append(m)
        return results

    @staticmethod
    def find_by_modality(modality: str) -> List[Dict[str, Any]]:
        return [m for m in ModelRegistry.list() if m.get("modality") == modality and m.get("enabled")]

    @staticmethod
    def find_by_provider(provider_id: str) -> List[Dict[str, Any]]:
        return [m for m in ModelRegistry.list() if m.get("provider_id") == provider_id]

    # Compatibility stubs for older UI calls
    @staticmethod
    def scan_local_providers():
        from lmms.backend.logic.manager import backend_manager
        return backend_manager.provider.scan_all_models()
        
    @staticmethod
    def get_model(model_id: str):
        # Fallback to internal_id matching or raw model_id
        for m in ModelRegistry.list():
            if m["model_id"] == model_id or m["id"] == model_id:
                return m
        return None
        
    @staticmethod
    def remove_model(model_id: str):
        for m in ModelRegistry.list():
            if m["model_id"] == model_id or m["id"] == model_id:
                ModelRegistry.delete(m["id"])
                
    @staticmethod
    def save_model_profile(model_id: str, profile: dict):
        # Maps old profile saving to metadata
        for m in ModelRegistry.list():
            if m["model_id"] == model_id or m["id"] == model_id:
                meta = m.get("metadata", {})
                meta["profile"] = profile
                ModelRegistry.update(m["id"], {"metadata": meta})

    @staticmethod
    def get_model_profile(model_id: str):
        for m in ModelRegistry.list():
            if m["model_id"] == model_id or m["id"] == model_id:
                return m.get("metadata", {}).get("profile", {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "context_length": 4096,
                    "gpu_layers": -1,
                    "system_prompt": "You are a helpful AI assistant."
                })
        return {}
