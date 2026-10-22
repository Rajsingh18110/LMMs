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

"""Universal Model Provider Registry supporting 50+ local and cloud providers with common schema."""

import os
import json
import urllib.request
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from .provider_presets import PROVIDER_PRESETS

PROVIDERS_FILE = os.path.expanduser("~/.lmms/providers.json")


class ProviderRegistry:
    """Generic Provider Registry managing 50+ local and cloud providers with unified schema."""

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
    def list_presets() -> Dict[str, Dict[str, Any]]:
        """Returns the dictionary of all 50+ preconfigured provider definitions."""
        return PROVIDER_PRESETS

    @staticmethod
    def create(
        name: str,
        p_type: str,
        base_url: str,
        api_key: str = "",
        webhook_url: str = "",
        category: str = "text",
        headers: Optional[Dict[str, str]] = None,
        models: Optional[List[str]] = None,
        default_model: str = "",
        fallback_model: str = "",
        timeout: float = 60.0,
    ) -> str:
        p_id = str(uuid.uuid4())
        return ProviderRegistry.create_with_id(
            p_id=p_id,
            name=name,
            p_type=p_type,
            base_url=base_url,
            api_key=api_key,
            webhook_url=webhook_url,
            category=category,
            headers=headers,
            models=models,
            default_model=default_model,
            fallback_model=fallback_model,
            timeout=timeout,
        )

    @staticmethod
    def create_from_preset(preset_id: str, api_key: str = "", base_url_override: str = "") -> Optional[str]:
        """Instantiates a provider from the 50+ presets with optional key and URL overrides."""
        preset = PROVIDER_PRESETS.get(preset_id)
        if not preset:
            return None
        return ProviderRegistry.create(
            name=preset["name"],
            p_type=preset["type"],
            base_url=base_url_override or preset["base_url"],
            api_key=api_key,
            category=preset.get("category", "cloud"),
            models=preset.get("models", []),
            default_model=preset.get("default_model", ""),
        )

    @staticmethod
    def create_with_id(
        p_id: str,
        name: str,
        p_type: str,
        base_url: str,
        api_key: str = "",
        webhook_url: str = "",
        category: str = "text",
        headers: Optional[Dict[str, str]] = None,
        models: Optional[List[str]] = None,
        default_model: str = "",
        fallback_model: str = "",
        timeout: float = 60.0,
    ) -> str:
        data = ProviderRegistry._load_raw()

        provider = {
            "id": p_id,
            "name": name,
            "type": p_type,
            "category": category,
            "enabled": True,
            "base_url": base_url,
            "api_key": api_key,
            "webhook_url": webhook_url,
            "headers": headers or {},
            "models": models or [],
            "default_model": default_model,
            "fallback_model": fallback_model,
            "timeout": timeout,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
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
        allowed_keys = [
            "name",
            "base_url",
            "api_key",
            "webhook_url",
            "enabled",
            "type",
            "category",
            "headers",
            "models",
            "default_model",
            "fallback_model",
            "timeout",
        ]
        for k, v in updates.items():
            if k in allowed_keys:
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
            safe = ProviderRegistry.get_safe(p_id)
            if safe:
                results.append(safe)
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

    @staticmethod
    def test_connection(p_id: str) -> Dict[str, Any]:
        """Pings provider endpoint to test health and verify authentication."""
        provider = ProviderRegistry.get(p_id)
        if not provider:
            return {"success": False, "error": f"Provider {p_id} not found."}

        base_url = provider.get("base_url", "").rstrip("/")
        api_key = provider.get("api_key", "")
        headers = dict(provider.get("headers", {}))
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Standard OpenAI models endpoint or base URL ping
        test_url = f"{base_url}/models" if not base_url.endswith("/models") else base_url

        try:
            req = urllib.request.Request(test_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                code = resp.status
                body = resp.read().decode("utf-8", errors="ignore")
                try:
                    parsed = json.loads(body)
                    models_found = [m.get("id") for m in parsed.get("data", []) if isinstance(m, dict) and "id" in m]
                    return {
                        "success": True,
                        "status_code": code,
                        "discovered_models": models_found[:15],
                        "message": f"Successfully connected to {provider['name']} (HTTP {code}).",
                    }
                except Exception:
                    return {
                        "success": True,
                        "status_code": code,
                        "message": f"Endpoint responded with HTTP {code}.",
                    }
        except urllib.error.HTTPError as he:
            return {
                "success": False,
                "status_code": he.code,
                "error": f"HTTP Error {he.code}: {he.reason}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {e}",
            }
