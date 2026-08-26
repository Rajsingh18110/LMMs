import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Base storage path for provider configuration
PROVIDERS_FILE = os.path.expanduser("~/.lmms/providers.json")

class ProviderRegistry:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(PROVIDERS_FILE), exist_ok=True)
        
    @staticmethod
    def _load_raw() -> Dict[str, Any]:
        if not os.path.exists(PROVIDERS_FILE):
            return {}
        try:
            with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
            
    @staticmethod
    def _save_raw(data: Dict[str, Any]):
        ProviderRegistry._ensure_dir()
        with open(PROVIDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def create(name: str, p_type: str, base_url: str, api_key: str = "", webhook_url: str = "") -> str:
        data = ProviderRegistry._load_raw()
        p_id = str(uuid.uuid4())
        
        # TODO: In future, integrate with OS Keychain for api_key.
        # For now we store it, but when retrieving via `get_safe()`, we mask it.
        provider = {
            "id": p_id,
            "name": name,
            "type": p_type,
            "enabled": True,
            "base_url": base_url,
            "api_key": api_key, # Consider encryption here
            "webhook_url": webhook_url,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        data[p_id] = provider
        ProviderRegistry._save_raw(data)
        return p_id

    @staticmethod
    def update(p_id: str, updates: Dict[str, Any]) -> bool:
        data = ProviderRegistry._load_raw()
        if p_id not in data:
            return False
            
        provider = data[p_id]
        for k, v in updates.items():
            if k in ["name", "base_url", "api_key", "webhook_url", "enabled", "type"]:
                provider[k] = v
        
        provider["updated_at"] = datetime.utcnow().isoformat()
        ProviderRegistry._save_raw(data)
        return True

    @staticmethod
    def get(p_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full provider config (including api_key for internal use)."""
        data = ProviderRegistry._load_raw()
        return data.get(p_id)

    @staticmethod
    def get_safe(p_id: str) -> Optional[Dict[str, Any]]:
        """Returns the provider config with the api_key masked for UI/API."""
        provider = ProviderRegistry.get(p_id)
        if not provider:
            return None
        safe_provider = dict(provider)
        key = safe_provider.get("api_key", "")
        if key:
            safe_provider["api_key"] = f"{key[:4]}••••••••{key[-4:]}" if len(key) >= 8 else "Configured"
        return safe_provider

    @staticmethod
    def list_safe() -> List[Dict[str, Any]]:
        """Returns a list of all providers safely masked."""
        data = ProviderRegistry._load_raw()
        results = []
        for p_id in data.keys():
            results.append(ProviderRegistry.get_safe(p_id))
        return results
        
    @staticmethod
    def delete(p_id: str) -> bool:
        data = ProviderRegistry._load_raw()
        if p_id in data:
            del data[p_id]
            ProviderRegistry._save_raw(data)
            return True
        return False
        
    @staticmethod
    def enable(p_id: str) -> bool:
        return ProviderRegistry.update(p_id, {"enabled": True})
        
    @staticmethod
    def disable(p_id: str) -> bool:
        return ProviderRegistry.update(p_id, {"enabled": False})
