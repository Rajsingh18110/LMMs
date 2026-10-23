# Copyright 2026 LMMs Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Persistent Online Models Registry.
Manages online API providers (Anthropic, OpenAI, Gemini, Sarvam AI, DeepSeek, Groq, etc.)
and custom webhooks in ~/.lmms/config/online_models.json.
"""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

ONLINE_MODELS_FILE = os.path.expanduser("~/.lmms/config/online_models.json")


class OnlineModelRegistry:
    """Manages configured online model endpoints, API credentials, and active online model state."""

    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(ONLINE_MODELS_FILE), exist_ok=True)

    @staticmethod
    def _load() -> Dict[str, Any]:
        OnlineModelRegistry._ensure_dir()
        if not os.path.exists(ONLINE_MODELS_FILE):
            default_data = {
                "active_model_id": None,
                "active_type": "offline",  # "offline" or "online"
                "models": {}
            }
            OnlineModelRegistry._save(default_data)
            return default_data

        try:
            with open(ONLINE_MODELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active_model_id": None, "active_type": "offline", "models": {}}

    @staticmethod
    def _save(data: Dict[str, Any]):
        OnlineModelRegistry._ensure_dir()
        with open(ONLINE_MODELS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def list_models(safe: bool = True) -> List[Dict[str, Any]]:
        """Returns all configured online models. If safe=True, masks API keys."""
        data = OnlineModelRegistry._load()
        models = []
        for m_id, m in data.get("models", {}).items():
            item = dict(m)
            if safe and item.get("api_key"):
                k = item["api_key"]
                item["api_key_masked"] = f"{k[:4]}••••••••{k[-4:]}" if len(k) >= 8 else "••••••••"
            models.append(item)
        return models

    @staticmethod
    def get_model(model_id: str) -> Optional[Dict[str, Any]]:
        """Returns the full model config including raw api_key for generation."""
        data = OnlineModelRegistry._load()
        models = data.get("models", {})
        if model_id in models:
            return models[model_id]
        
        # Fuzzy / name match
        for m in models.values():
            if m.get("name", "").lower() == model_id.lower() or m.get("id", "").lower() == model_id.lower():
                return m
        return None

    @staticmethod
    def get_active_model() -> Optional[Dict[str, Any]]:
        """Returns the active online model if active_type is 'online'."""
        data = OnlineModelRegistry._load()
        if data.get("active_type") != "online":
            return None
        active_id = data.get("active_model_id")
        if not active_id:
            return None
        return OnlineModelRegistry.get_model(active_id)

    @staticmethod
    def get_active_type() -> str:
        """Returns 'offline' or 'online'."""
        data = OnlineModelRegistry._load()
        return data.get("active_type", "offline")

    @staticmethod
    def set_active_model(model_id: Optional[str], active_type: str = "online"):
        """Sets the active model and active type."""
        data = OnlineModelRegistry._load()
        data["active_model_id"] = model_id
        data["active_type"] = active_type
        OnlineModelRegistry._save(data)

    @staticmethod
    def is_online_model(name_or_id: str) -> bool:
        """Checks if a model name or id belongs to the online registry."""
        return OnlineModelRegistry.get_model(name_or_id) is not None

    @staticmethod
    def add_model(
        name: str,
        provider_id: str,
        provider_name: str,
        model_id: str,
        p_type: str = "openai_compatible",
        base_url: str = "",
        api_key: str = "",
        webhook_url: str = "",
        custom_headers: Optional[Dict[str, str]] = None,
        category: str = "general",
        set_active: bool = False
    ) -> str:
        """Adds or updates an online model entry."""
        data = OnlineModelRegistry._load()
        entry_id = str(uuid.uuid4())[:8]
        unique_key = f"{provider_id}:{model_id}" if provider_id != "custom_webhook" else f"webhook:{entry_id}"

        model_entry = {
            "key": unique_key,
            "id": model_id,
            "name": name or model_id,
            "provider_id": provider_id,
            "provider_name": provider_name,
            "type": p_type,
            "base_url": base_url.rstrip("/"),
            "api_key": api_key.strip(),
            "webhook_url": webhook_url.strip(),
            "custom_headers": custom_headers or {},
            "category": category,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        data.setdefault("models", {})[unique_key] = model_entry

        if set_active or data.get("active_model_id") is None:
            data["active_model_id"] = unique_key
            data["active_type"] = "online"

        OnlineModelRegistry._save(data)
        return unique_key

    @staticmethod
    def remove_model(key: str) -> bool:
        """Deletes a configured online model."""
        data = OnlineModelRegistry._load()
        if key in data.get("models", {}):
            del data["models"][key]
            if data.get("active_model_id") == key:
                data["active_model_id"] = None
                data["active_type"] = "offline"
            OnlineModelRegistry._save(data)
            return True
        return False
