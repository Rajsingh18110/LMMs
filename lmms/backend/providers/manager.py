from typing import List, Dict, Any, Optional
from lmms.backend.core.registry.provider_registry import ProviderRegistry
from lmms.backend.contracts.provider import ProviderContract

class ProviderManager:
    """
    Coordinates across all model providers (Local and External) based on the ProviderRegistry.
    """
    def __init__(self):
        self._adapters: Dict[str, ProviderContract] = {}
        self.reload_providers()

    def reload_providers(self):
        """Re-initializes all enabled providers from the registry."""
        self._adapters.clear()
        
        provider_configs = ProviderRegistry.list_safe()
        for p_safe in provider_configs:
            p_id = p_safe["id"]
            
            # Need to get the real config with API keys to initialize adapter
            real_config = ProviderRegistry.get(p_id)
            if not real_config or not real_config.get("enabled", False):
                continue
                
            ptype = real_config.get("type", "").lower()
            
            if ptype == "openai_compatible":
                from lmms.backend.providers.adapters.openai_compatible import OpenAICompatibleProvider
                self._adapters[p_id] = OpenAICompatibleProvider(p_id, real_config)
            
            # TODO: Add Local (LlamaCpp/Ollama) adapters here as they are ported to the new contract.

    def get_provider(self, provider_id: str) -> Optional[ProviderContract]:
        return self._adapters.get(provider_id)
        
    def scan_all_models(self) -> List[Dict[str, Any]]:
        """Scans all registered enabled providers and returns models."""
        all_models = []
        for p_id, adapter in self._adapters.items():
            try:
                models = adapter.scan_models()
                all_models.extend(models)
            except Exception as e:
                print(f"Error scanning provider {p_id}: {e}")
        return all_models

